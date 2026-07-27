import argparse
import sys
import os
import contextlib
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse

from src import config
from src import database
from src import writer
from src import tts
from src import audio
from src import telegram_uploader
from src import video
from src import shorts_generator
from src import youtube_uploader

def safe_print(*args, **kwargs):
    """Safely print message preventing UnicodeEncodeError on Windows terminals."""
    msg = " ".join(str(arg) for arg in args)
    try:
        sys.stdout.write(msg + kwargs.get("end", "\n"))
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or 'utf-8'
            sys.stdout.write(msg.encode(encoding, errors='replace').decode(encoding) + kwargs.get("end", "\n"))
            sys.stdout.flush()
        except Exception:
            sys.stdout.write(msg.encode('ascii', errors='replace').decode('ascii') + kwargs.get("end", "\n"))
            sys.stdout.flush()

print = safe_print

# Initialize FastAPI App
app = FastAPI(title="Truyện 24h Audio Engine", version="1.0.0")


class CallbackStream:
    def __init__(self, original_stream, callback):
        self.original_stream = original_stream
        self.callback = callback
        
    def write(self, data):
        self.original_stream.write(data)
        if data.strip():
            self.callback(data.strip())
            
    def flush(self):
        self.original_stream.flush()

def run_chapter_pipeline(novel_id: str, log_callback=None):
    """Executes the full pipeline for writing a chapter and uploading audio."""
    if log_callback:
        stream = CallbackStream(sys.stdout, log_callback)
        with contextlib.redirect_stdout(stream):
            _run_chapter_pipeline_impl(novel_id)
    else:
        _run_chapter_pipeline_impl(novel_id)

def _run_chapter_pipeline_impl(novel_id: str):
    """Internal implementation of the pipeline."""
    if not config.validate_config():
        print("[ERROR] Configuration validation failed. Aborting pipeline.")
        return
        
    try:
        # 1. Write the chapter & update Story Bible
        chapter = writer.write_next_chapter(novel_id)
        chapter_id = chapter["id"]
        chapter_num = chapter["chapter_number"]
        chapter_title = chapter["title"]
        chapter_content = chapter["content"]
        
        print(f"[INFO] Chapter {chapter_num} written successfully: '{chapter_title}'")
        
        # 2. Convert chapter text to raw speech audio & subtitles
        raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter_content, chapter_id)
        
        # 3. Mix speech audio with background music
        final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
        
        # 4. Render Video Dài (16:9) qua AI-auto-generate-video / FFmpeg
        print(f"[INFO] Bắt đầu render video dài (16:9) cho Chương {chapter_num}...")
        video_path = video.render_novel_video(final_audio_path, srt_path, chapter_title, chapter_id)
        if video_path:
            print(f"[INFO] Video dài đã được tạo tại: {video_path}")
            database.update_chapter_video_status(chapter_id, status="completed", video_url=video_path)
            
        # 5. Render Video Shorts (9:16) 45s cao trào cho YouTube Shorts / TikTok
        print(f"[INFO] Bắt đầu render Video Shorts (9:16) cho Chương {chapter_num}...")
        shorts_path = shorts_generator.generate_shorts_video(final_audio_path, srt_path, chapter_id, chapter_title)
        if shorts_path:
            print(f"[INFO] Video Shorts đã được tạo tại: {shorts_path}")
            
        # 6. (Tạm thời bỏ qua Upload YouTube - Đã tắt theo yêu cầu)
        # print(f"[INFO] Bỏ qua upload YouTube. Tập trung gửi Telegram Channel...")
        # if video_path and os.path.exists(video_path):
        #     youtube_url = youtube_uploader.upload_video_to_youtube(video_path, chapter_title, chapter_num)
        #     if youtube_url:
        #         database.update_chapter_video_status(chapter_id, status="published", video_url=youtube_url)
        
        # 7. Upload file Audio, Subtitles & Video MP4 lên kênh Telegram
        caption_markdown = (
            f"🎙️ *Truyện 24h Audio - Tập {chapter_num}*\n\n"
            f"📖 *Chương {chapter_num}: {chapter_title}*\n\n"
            f"Tác phẩm được viết tự động bằng AI, chỉnh sửa âm thanh & video chất lượng cao."
        )
        
        success = telegram_uploader.send_audio_to_telegram(
            audio_path=final_audio_path,
            caption=caption_markdown,
            title=f"Chương {chapter_num} - {chapter_title}",
            srt_path=srt_path
        )
        
        # Gửi video MP4 dài (16:9) và Video Shorts (9:16) lên Telegram
        if video_path and os.path.exists(video_path):
            telegram_uploader.send_video_to_telegram(video_path, f"🎬 *Video Full 16:9 - Chương {chapter_num}: {chapter_title}*")
        if shorts_path and os.path.exists(shorts_path):
            telegram_uploader.send_video_to_telegram(shorts_path, f"📱 *Video Shorts 9:16 - Chương {chapter_num}: {chapter_title}*")
        
        if success:
            print(f"[INFO] Pipeline execution complete for Chapter {chapter_num}!")
            database.update_chapter_audio(chapter_id, "Completed All Media & Uploads")
        else:
            print("[WARNING] Pipeline finished but Telegram upload failed.")
            
    except Exception as e:
        print(f"[ERROR] Critical error in pipeline execution: {e}")

# FastAPI endpoints
@app.get("/", response_class=HTMLResponse)
def index():
    """Simple status page for UptimeRobot / Cron-job.org pings."""
    return """
    <html>
        <head>
            <title>Truyện 24h Audio Engine</title>
            <style>
                body { font-family: sans-serif; background-color: #121212; color: #ffffff; text-align: center; padding-top: 100px; }
                h1 { color: #00e676; }
                .status { background: #1e1e1e; padding: 20px; border-radius: 8px; display: inline-block; }
            </style>
        </head>
        <body>
            <h1>Truyện 24h Audio</h1>
            <div class="status">
                <p>Trạng thái hệ thống: 🟢 Hoạt động 24/24</p>
                <p>Sử dụng: edge-tts + Gemini 1.5 Flash + Supabase</p>
            </div>
        </body>
    </html>
    """

@app.post("/run-pipeline")
def trigger_pipeline(novel_id: str, background_tasks: BackgroundTasks):
    """Triggers the chapter writing & audio publishing pipeline asynchronously."""
    background_tasks.add_task(run_chapter_pipeline, novel_id)
    return {"status": "accepted", "message": "Pipeline execution started in the background."}

# CLI Argument Parser
def main():
    parser = argparse.ArgumentParser(description="Truyen 24h Audio CLI Orchestrator")
    parser.add_argument("--action", choices=["init-novel", "run-pipeline", "export-audio", "serve"], 
                        default="serve", help="Action to perform. Default is 'serve' web app.")
    parser.add_argument("--title", help="Novel title for 'init-novel'")
    parser.add_argument("--desc", help="Novel description for 'init-novel'")
    parser.add_argument("--novel-id", help="Novel UUID for 'run-pipeline'")
    parser.add_argument("--chapter-id", help="Chapter UUID for 'export-audio'")
    
    args = parser.parse_args()
    
    if args.action == "serve":
        # Launch FastAPI server (Default port 7860 for Hugging Face)
        port = int(os.getenv("PORT", 7860))
        print(f"[INFO] Starting server on port {port}...")
        uvicorn.run(app, host="0.0.0.0", port=port)
        
    elif args.action == "init-novel":
        if not config.validate_config():
            sys.exit(1)
        title = args.title
        desc = args.desc or ""
        
        if not title:
            safe_print("[INFO] No title provided. Brainstorming novel concept using Gemini...")
            try:
                import json
                import re
                from templates import prompts
                brainstorm_json = writer.call_gemini(prompts.BRAINSTORM_PROMPT, json_mode=True)
                cleaned_json = brainstorm_json.strip()
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_json)
                if match:
                    cleaned_json = match.group(1).strip()
                brainstorm_data = json.loads(cleaned_json)
                title = brainstorm_data.get("title", "Huyen Thoai Troi Day")
                desc = brainstorm_data.get("description", "Mot cau chuyen gia tuong ky thu.")
                safe_print(f"[INFO] Generated Title: '{title}'")
                safe_print(f"[INFO] Generated Description: '{desc[:150]}...'")
            except Exception as e:
                safe_print(f"[ERROR] Failed to brainstorm novel: {e}")
                title = "Huyen Thoai Aetheria"
                desc = "Cau chuyen gia tuong day loi cuon."
                safe_print(f"[INFO] Using fallback Title: '{title}'")
                
        novel = writer.init_novel_pipeline(title, desc)
        safe_print(f"SUCCESS: Novel initialized. ID: {novel['id']}")
        
    elif args.action == "run-pipeline":
        novel_id = args.novel_id
        if novel_id:
            novel_id = novel_id.strip().strip("'\"").strip()
        if not novel_id or novel_id.lower() == "all":
            if not config.validate_config():
                sys.exit(1)
            active_novels = database.get_active_novels()
            if not active_novels:
                safe_print("[INFO] No active novels found in database with status 'writing'.")
                sys.exit(0)
            
            safe_print(f"[INFO] Found {len(active_novels)} active novels. Executing pipelines...")
            for novel in active_novels:
                safe_print("\n=========================================")
                safe_print(f"EXECUTING PIPELINE FOR: {novel['title']} (ID: {novel['id']})")
                safe_print("=========================================")
                try:
                    run_chapter_pipeline(novel['id'])
                except Exception as e:
                    safe_print(f"[ERROR] Failed running pipeline for {novel['title']}: {e}")
        else:
            run_chapter_pipeline(novel_id)
        
    elif args.action == "export-audio":
        chapter_id = getattr(args, "chapter_id", None)
        if not chapter_id:
            print("[ERROR] --chapter-id is required for export-audio action.")
            sys.exit(1)
        if not config.validate_config():
            sys.exit(1)
        
        # Fetch chapter content
        client = database.get_client()
        response = client.table("chapters").select("*").eq("id", chapter_id).execute()
        if not response.data:
            print(f"[ERROR] Chapter not found with ID {chapter_id}")
            sys.exit(1)
            
        chapter = response.data[0]
        raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter["content"], chapter_id)
        final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
        
        telegram_uploader.send_audio_to_telegram(
            audio_path=final_audio_path,
            caption=f"🎙️ Trích xuất âm thanh: {chapter['title']}",
            title=chapter["title"],
            srt_path=srt_path
        )
        print("SUCCESS: Audio exported and sent.")

if __name__ == "__main__":
    # If no arguments provided and not in terminal CLI context, default to serve
    if len(sys.argv) == 1:
        sys.argv.append("--action")
        sys.argv.append("serve")
    main()
