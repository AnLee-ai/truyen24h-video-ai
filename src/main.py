import argparse
import sys
import os
import json
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
from src import thumbnail_generator

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

def find_chapter_needing_video(novel_id: str) -> dict:
    """
    Tự động quét các chương đã viết trong CSDL & File Cục Bộ:
    Nếu phát hiện chương nào ĐÃ CÓ NỘI DUNG VĂN BẢN nhưng CHƯA TẠO VIDEO và CHƯA HOÀN THÀNH,
    thì mới trả về để render Video. Ngược lại, nếu chương đó ĐÃ HOÀN THÀNH thì bỏ qua để viết chương mới (Chương 2, 3, 4...).
    """
    import os, json
    completed_set = set()
    prog_file = "data/chapters_progress.json"
    if os.path.exists(prog_file):
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                pdata = json.load(f)
                raw_list = pdata.get("completed_chapters", [])
                for item in raw_list:
                    completed_set.add(item)
                    completed_set.add(str(item))
                    if str(item).isdigit():
                        completed_set.add(int(item))
        except Exception:
            pass

    try:
        all_chapters = database.get_all_chapters(novel_id)
        for ch in all_chapters:
            ch_id = str(ch.get("id", ""))
            ch_content = str(ch.get("content", ""))
            ch_num = int(ch.get("chapter_number", 0)) if str(ch.get("chapter_number", "")).isdigit() else 0
            v_status = str(ch.get("video_status", "")).strip().lower()
            v_url = str(ch.get("video_url", "")).strip()
            audio_url = str(ch.get("audio_url", "")).strip().lower()
            
            # 1. Bỏ qua nếu chương nằm trong danh sách đã hoàn thành local hoặc Supabase
            if ch_num in completed_set or str(ch_num) in completed_set or ch_id in completed_set:
                print(f"[INFO] 🛡️ Bỏ qua Chương {ch_num} (ID: {ch_id}) vì ĐÃ HOÀN THÀNH trong data/chapters_progress.json.")
                continue

            # 2. Bỏ qua nếu video_status hoặc video_url hoặc audio_url đã đánh dấu hoàn thành
            if v_status in ["completed", "published", "done", "true"] or "completed" in audio_url or bool(v_url):
                print(f"[INFO] 🛡️ Bỏ qua Chương {ch_num} (ID: {ch_id}) vì ĐÃ HOÀN THÀNH trên Supabase (video_status={v_status}).")
                # Đánh dấu bổ sung vào local file
                database.record_completed_chapter_local(ch_id, ch_num)
                continue
                
            # 3. Bỏ qua nếu chưa viết xong nội dung (còn là BLUEPRINT hoặc < 1000 từ)
            if not ch_content or ch_content.startswith("BLUEPRINT:") or len(ch_content.split()) < 1000:
                continue
                
            # Kiểm tra xem chương này có cần làm video không
            print(f"[INFO] 🎯 TỰ ĐỘNG PHÁT HIỆN CHƯƠNG CHƯA HOÀN THÀNH: Chương {ch_num} (ID: {ch_id}) đang cần xử lý Media/Video!")
            return ch
    except Exception as e:
        print(f"[WARNING] Lỗi quét chương chưa có video: {e}")
        
    return {}

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
        # 0. TỰ ĐỘNG PHÁT HIỆN CHƯƠNG ĐÃ CÓ AUDIO NHƯNG CHƯA CÓ VIDEO (ƯU TIÊN RENDER VIDEO NGAY)
        pending_video_ch = find_chapter_needing_video(novel_id)
        is_resuming_video = False
        if pending_video_ch:
            chapter = pending_video_ch
            chapter_id = chapter["id"]
            chapter_num = chapter["chapter_number"]
            chapter_title = chapter["title"]
            chapter_content = chapter["content"]
            is_resuming_video = True
            print(f"[INFO] TRỰC TIẾP BỎ QUA BƯỚC VIẾT CHƯƠNG MỚI! Tập trung render Video ngay cho Chương {chapter_num}: '{chapter_title}' (Words: {len(chapter_content.split())})...")
        else:
            # 1. Viết chương tiếp theo nếu tất cả các chương cũ đã có video đầy đủ
            chapter = writer.write_next_chapter(novel_id)
            chapter_id = chapter["id"]
            chapter_num = chapter["chapter_number"]
            chapter_title = chapter["title"]
            chapter_content = chapter["content"]
            print(f"[INFO] Chapter {chapter_num} written successfully: '{chapter_title}' (Words: {len(chapter_content.split())})")
        
        # BỘ KIỂM DUYỆT BẢO VỆ TUYỆT ĐỐI (Strict Quality Guardrail cho chương VIẾT MỚI):
        # Khi viết chương mới, NẾU NỘI DUNG CHƯƠNG CHƯA ĐẠT MỐC >2500 TỪ thì dừng.
        # Nhưng khi DÙNG LẠI CHƯƠNG CŨ ĐÃ CÓ AUDIO (is_resuming_video=True), CHO PHÉP TẠO VIDEO TRỰC TIẾP!
        if not is_resuming_video and (not chapter_content or len(chapter_content.split()) < 2500):
            print(f"[WARNING] Nội dung chương viết mới chưa đạt tiêu chuẩn BẮT BUỘC (>2500 từ). Độ dài thực tế: {len(chapter_content.split()) if chapter_content else 0} từ. Tự động dừng tiến trình an toàn.")
            return
            
        # 2. CHẾ ĐỘ TỰ ĐỘNG LÀM LẠI BẮT BUỘC: Ép thời lượng Audio & Video kéo dài > 10 PHÚT (Tối thiểu 600 giây)
        final_audio_path = ""
        srt_path = ""
        max_duration_attempts = 3
        
        for duration_attempt in range(max_duration_attempts):
            if duration_attempt > 0:
                print(f"\n[WARNING] ⚡ KÍCH HOẠT CHẾ ĐỘ LÀM LẠI (Lượt {duration_attempt + 1}/{max_duration_attempts}): "
                      f"Thời lượng audio cũ chưa đạt >10 phút. Tự động gọi AI viết nối dài phân cảnh kịch tính...")
                chapter_content = writer.expand_chapter_content(chapter_content, target_words=2800)
                database.create_chapter(novel_id, chapter_num, chapter_title, chapter_content)
                
            # Convert chapter text to raw speech audio & subtitles
            raw_audio_path, srt_path = tts.generate_voice_and_subs(chapter_content, chapter_id)
            
            # Mix speech audio with background music
            final_audio_path = audio.mix_bgm_with_voice(raw_audio_path, chapter_id)
            
            # Đo chính xác thời lượng thực tế của file Audio
            current_duration = video.get_audio_duration_seconds(final_audio_path)
            print(f"[INFO] ⏱️ Thời lượng Audio thực tế của Tập {chapter_num}: {current_duration:.1f} giây ({current_duration/60:.2f} phút).")
            
            if current_duration >= 600.0:
                print(f"[SUCCESS] 🟢 THỜI LƯỢNG ĐẠT CHUẨN > 10 PHÚT! ({current_duration/60:.2f} phút >= 10.0 phút). Tiến hành render Video...")
                break
            else:
                print(f"[WARNING] 🔴 CHẾ ĐỘ LÀM LẠI: Thời lượng {current_duration/60:.2f} phút CHƯA ĐẠT MỐC >10 PHÚT (<600s). Đang chuẩn bị gọi AI làm lại & mở rộng kịch bản...")
                # Gọi AI mở rộng kịch bản chương truyện lên ~2800 từ (13-15 phút)
                chapter_content = writer.expand_chapter_content(chapter_content, target_words=2800)
                database.create_chapter(novel_id, chapter_num, chapter_title, chapter_content)
                if duration_attempt == max_duration_attempts - 1:
                    print(f"[INFO] Đã thử làm lại {max_duration_attempts} lần. Tiếp tục tiến trình với thời lượng hiện tại.")
        
        # Tự động tìm lại file SRT phụ đề nếu bị thiếu
        if not srt_path or not os.path.exists(srt_path):
            possible_srt_paths = [
                os.path.join("output", chapter_id, f"{chapter_id}.srt"),
                os.path.join("output", chapter_id, "subtitles.srt"),
                os.path.join("output", chapter_id, "chapter.srt")
            ]
            for p_srt in possible_srt_paths:
                if os.path.exists(p_srt):
                    srt_path = p_srt
                    print(f"[INFO] 🎯 Đã tự động khôi phục file SRT phụ đề tại: {srt_path}")
                    break

        # 4. Render Video Dài (16:9) qua AI-auto-generate-video / FFmpeg
        print(f"[INFO] Bắt đầu render video dài (16:9) cho Chương {chapter_num}...")
        video_path = video.render_novel_video(final_audio_path, srt_path, chapter_title, chapter_id)
        video_public_url = ""
        if video_path:
            print(f"[INFO] Video dài đã được tạo tại: {video_path}")
            video_public_url = database.upload_file_to_supabase(video_path, bucket_name="media", destination_path=f"videos/full/{chapter_id}_16_9.mp4")
            database.update_chapter_video_status(chapter_id, status="completed", video_url=video_public_url or video_path)
            
        # 4b. Tự động thiết kế Ảnh Bìa Thumbnail 16:9 YouTube 4K siêu bắt mắt
        scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
        thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num}...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, scene_img_p, thumb_out_p)
        if thumbnail_path and os.path.exists(thumbnail_path):
            database.upload_file_to_supabase(thumbnail_path, bucket_name="media", destination_path=f"thumbnails/{chapter_id}_thumbnail.jpg")
            
        # 5. (Đã tắt phần render Video Shorts 9:16 theo yêu cầu người dùng)
        shorts_path = ""
        # print(f"[INFO] Bắt đầu render Video Shorts (9:16) cho Chương {chapter_num}...")
        # shorts_path = shorts_generator.generate_shorts_video(final_audio_path, srt_path, chapter_id, chapter_title)

        # 5b. Tải toàn bộ Ảnh AI 2D của chương lên Supabase Storage
        img_dir = os.path.join("output", chapter_id, "images")
        if os.path.exists(img_dir):
            for img_name in os.listdir(img_dir):
                if img_name.endswith((".jpg", ".png", ".jpeg")):
                    img_p = os.path.join(img_dir, img_name)
                    database.upload_file_to_supabase(img_p, bucket_name="media", destination_path=f"images/{chapter_id}/{img_name}")
            
        # 6. (Tạm thời bỏ qua Upload YouTube - Đã tắt theo yêu cầu)
        # print(f"[INFO] Bỏ qua upload YouTube. Tập trung gửi Telegram Channel...")
        # if video_path and os.path.exists(video_path):
        #     youtube_url = youtube_uploader.upload_video_to_youtube(video_path, chapter_title, chapter_num)
        #     if youtube_url:
        #         database.update_chapter_video_status(chapter_id, status="published", video_url=youtube_url)
        
        # 7. Upload file Audio, Subtitles, Thumbnail 16:9 & Video MP4 16:9 lên kênh Telegram
        caption_markdown = telegram_uploader.generate_seo_caption(chapter_num, chapter_title)
        
        # Gửi Ảnh Bìa Thumbnail 16:9 4K lên Telegram
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"[INFO] Uploading 16:9 Thumbnail 4K to Telegram ({os.path.getsize(thumbnail_path)} bytes)...")
            thumb_caption = f"🖼️ *Ảnh Bìa Thumbnail 16:9 4K - Tập {chapter_num}: {chapter_title}*\n🔥 Thiết kế tự động phong cách MoneyPrinter/ComfyUI 16:9"
            telegram_uploader.send_photo_to_telegram(thumbnail_path, thumb_caption)

        success = telegram_uploader.send_audio_to_telegram(
            audio_path=final_audio_path,
            caption=caption_markdown,
            title=f"Chương {chapter_num} - {chapter_title}",
            srt_path=srt_path
        )
        
        # Gửi video MP4 dài (16:9) lên Telegram
        if video_path and os.path.exists(video_path):
            print(f"[INFO] Uploading Full 16:9 Video to Telegram ({os.path.getsize(video_path)} bytes)...")
            v_ok = telegram_uploader.send_video_to_telegram(video_path, f"🎬 *Video Full 16:9 - Chương {chapter_num}: {chapter_title}*", public_url=video_public_url)
            print(f"[INFO] Full Video Telegram upload result: {v_ok}")
        else:
            print(f"[WARNING] Video 16:9 path invalid or not found: {video_path}")
        
        # 8. Tự động Dọn Dẹp File Rác Chunks (Auto Disk Cleaner - Tiết kiệm 80% dung lượng ổ đĩa)
        try:
            ch_output_dir = os.path.join("output", chapter_id)
            if os.path.exists(ch_output_dir):
                for fname in os.listdir(ch_output_dir):
                    if "_chunk_" in fname or fname.endswith(("_tg_compressed.mp4", "concat_list.txt")):
                        fpath = os.path.join(ch_output_dir, fname)
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
                print(f"[INFO] 🧹 Auto Disk Cleaner: Đã dọn dẹp file tạm cho Tập {chapter_num} thành công.")
        except Exception as clean_err:
            print(f"[WARNING] Auto disk cleaner warning: {clean_err}")

        if success or (video_path and os.path.exists(video_path)):
            print(f"[INFO] Pipeline execution complete for Chapter {chapter_num}!")
            database.mark_chapter_completed_atomic(chapter_id, audio_url="Completed All Media & Uploads", video_url=video_public_url or "completed", chapter_number=chapter_num)
        else:
            print("[WARNING] Pipeline finished but Telegram upload failed. Preserving local completion state...")
            database.record_completed_chapter_local(chapter_id, chapter_num)
            
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
    parser.add_argument("--novel-id", nargs="?", default="", help="Novel UUID for 'run-pipeline'")
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
        # 1. Đọc ưu tiên tuyệt đối từ file data/active_novel.json (được Git theo dõi) hoặc output/current_novel.json
        file_novel_id = None
        novel_file = None
        if os.path.exists("data/active_novel.json"):
            novel_file = "data/active_novel.json"
        elif os.path.exists("output/current_novel.json"):
            novel_file = "output/current_novel.json"
            
        if novel_file:
            try:
                with open(novel_file, "r", encoding="utf-8") as f:
                    curr_n = json.load(f)
                    if curr_n.get("id"):
                        file_novel_id = curr_n["id"]
                        safe_print(f"[INFO] ⚡ PHÁT HIỆN BỘ TRUYỆN MỚI TỪ FILE '{novel_file}': '{curr_n.get('title')}' (ID: {file_novel_id})")
            except Exception as e:
                safe_print(f"[WARNING] Không thể đọc {novel_file}: {e}")

        # Cho file local đè hoàn toàn SECRET_NOVEL_ID trên GitHub secrets (chỉ dùng SECRET_NOVEL_ID nếu không có file local)
        novel_id = args.novel_id or os.getenv("INPUT_NOVEL_ID") or file_novel_id or os.getenv("SECRET_NOVEL_ID") or os.getenv("NOVEL_ID")
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
    g_raw = os.getenv("GEMINI_API_KEY", "").strip()
    mask_g = f"{g_raw[:4]}...{g_raw[-6:]}" if len(g_raw) >= 10 else "EMPTY"
    safe_print(f"[DEBUG] GitHub Secret GEMINI_API_KEY value: {mask_g}")
    
    if len(sys.argv) == 1:
        sys.argv.append("--action")
        sys.argv.append("run-pipeline")
    main()
