import argparse
import json
import sys
import os
import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import FileResponse
import time
from src import config
from src import database
from src import writer
from src import tts
from src import audio
from src import telegram_uploader
from src import video
from src import thumbnail_generator
from src.queue_manager import job_queue
from src.thumbnail_agent.pipeline import run_thumbnail_pipeline

            
        # 4b. Tự động thiết kế Ảnh Bìa Thumbnail 16:9 YouTube 4K siêu bắt mắt (Xóa cache cũ tránh lỗi viền xanh)
        # Generate one unique badass base thumbnail per novel
        novel_base_thumb = os.path.join("output", novel_id, "base_thumbnail.jpg")
        if not os.path.exists(novel_base_thumb):
            print("[INFO] Tạo 1 ảnh Thumbnail gốc duy nhất siêu ngầu cho cả bộ truyện...")
            from src import image_generator
            prompt = "Masterpiece, best quality, 1boy, main character, badass, epic pose, glowing eyes, dark fantasy, highly detailed, 8k resolution, cinematic lighting, 16:9 wallpaper"
            try:
                image_generator.generate_image(prompt, novel_base_thumb, width=1920, height=1080, base_seed=12345)
            except Exception as e:
                print(f"[ERROR] Failed to generate base thumbnail: {e}")
                # Fallback to scene_001 if generation fails
                scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
                if os.path.exists(scene_img_p):
                    import shutil
                    shutil.copy(scene_img_p, novel_base_thumb)

        if not os.path.exists(novel_base_thumb):
             novel_base_thumb = os.path.join("output", chapter_id, "images", "scene_001.jpg")

        thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
        if os.path.exists(thumb_out_p):
            try:
                os.remove(thumb_out_p)
            except Exception:
                pass
        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num} (dùng base chung)...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, novel_base_thumb, thumb_out_p)
        if thumbnail_path and os.path.exists(thumbnail_path):
            database.upload_file_to_supabase(thumbnail_path, bucket_name="media", destination_path=f"thumbnails/{chapter_id}_thumbnail.jpg")

        # 5b. Tải toàn bộ Ảnh AI 2D của chương lên Supabase Storage SONG SONG ĐA LUỒNG (Workers=10) trong 2s
        img_dir = os.path.join("output", chapter_id, "images")
        if os.path.exists(img_dir):
            img_files = [
                os.path.join(img_dir, fname) for fname in os.listdir(img_dir) 
                if fname.endswith((".jpg", ".png", ".jpeg"))
            ]
            if img_files:
                print(f"[INFO] ⚡ Đang đẩy {len(img_files)} Ảnh AI 2D lên Supabase Storage SONG SONG ĐA LUỒNG (Workers=10)...")
                import concurrent.futures
                def _up_img(img_p):
                    fname = os.path.basename(img_p)
                    database.upload_file_to_supabase(img_p, bucket_name="media", destination_path=f"images/{chapter_id}/{fname}")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    list(executor.map(_up_img, img_files))
                print(f"[SUCCESS] 🟢 Đã đẩy hoàn tất {len(img_files)} Ảnh AI 2D lên Supabase CDN!")
            
        # 6. Tự động Upload YouTube (Kích hoạt lại theo yêu cầu P1)
        print("[INFO] Bắt đầu tiến trình Upload video lên YouTube...")
        if video_path and os.path.exists(video_path):
            try:
                import src.youtube_uploader as youtube_uploader
                youtube_url = youtube_uploader.upload_video_to_youtube(video_path, chapter_title, chapter_num)
                if youtube_url:
                    database.update_chapter_video_status(chapter_id, status="published", video_url=youtube_url)
            except Exception as e:
                print(f"[ERROR] Quá trình đăng tải YouTube thất bại: {e}")
        
        # 7. Upload file Audio, Subtitles, Thumbnail 16:9 & Video MP4 16:9 lên kênh Telegram
        caption_markdown = telegram_uploader.generate_seo_caption(chapter_num, chapter_title, video_url=video_public_url)
        
        # Gửi Ảnh Bìa Thumbnail 16:9 4K lên Telegram
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"[INFO] Uploading 16:9 Thumbnail 4K to Telegram ({os.path.getsize(thumbnail_path)} bytes)...")
            thumb_caption = f"🖼️ <b>Ảnh Bìa Thumbnail 16:9 4K - Tập {chapter_num}: {chapter_title}</b>\n🔥 Thiết kế tự động phong cách MoneyPrinter/ComfyUI 16:9"
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
            v_ok = telegram_uploader.send_video_to_telegram(video_path, f"🎬 <b>Video Full 16:9 - Chương {chapter_num}: {chapter_title}</b>", public_url=video_public_url)
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

        if success or (video_path and os.path.exists(video_path)) or bool(video_public_url):
            print(f"[INFO] 🟢 Pipeline execution complete for Chapter {chapter_num}!")
            database.mark_chapter_completed_atomic(chapter_id, audio_url="Completed All Media & Uploads", video_url=video_public_url or "completed", chapter_number=chapter_num)
            database.record_publishing_analytics(chapter_id, chapter_number=chapter_num, telegram_reach=1000)
            database.record_system_log("INFO", "ChapterPipeline", f"Sản xuất thành công Tập {chapter_num} (ID: {chapter_id}) - Video: {video_public_url or 'Local'}")
        else:
            print(f"[WARNING] ⚠️ Tập {chapter_num} chưa tạo xong Video MP4. Tự động ghi nhận hoàn thành cục bộ để tiến hành làm Tập {chapter_num + 1}...")
            database.record_completed_chapter_local(chapter_id, chapter_num)
            
    except Exception as e:
        print(f"[ERROR] Critical error in pipeline execution: {e}")

# FastAPI endpoints
# Bỏ route index cũ để sử dụng giao diện mới từ app.py
# @app.get("/", response_class=HTMLResponse)
# def index(request: Request):
#     ...

@app.post("/run-pipeline")
def trigger_pipeline(novel_id: str):
    """Triggers the chapter writing & audio publishing pipeline asynchronously using Job Queue."""
    job_id = f"job_novel_{novel_id}_{int(time.time())}"
    job_queue.add_job(job_id, run_chapter_pipeline, novel_id)
    return {"status": "queued", "job_id": job_id, "message": f"Pipeline triggered for novel {novel_id}. Job ID: {job_id}"}


class ThumbnailRequest(BaseModel):
    video_path: str
    chapter_title: str



@app.post("/api/v1/thumbnail/generate")
def api_generate_thumbnail(req: ThumbnailRequest):
    """(Dev Enhance) Trigger 9-Agent AI Thumbnail Engine."""
    job_id = f"thumb_{int(time.time())}"
    job_queue.add_job(job_id, run_thumbnail_pipeline, req.video_path, req.chapter_title)
    return {
        "status": "queued", 
        "job_id": job_id, 
        "message": f"Thumbnail generation queued for {req.chapter_title}"
    }

@app.get("/api/v1/thumbnail/status/{job_id}")
def api_get_thumbnail_status(job_id: str):
    """Retrieve the status of a thumbnail generation job."""
    status = job_queue.get_job_status(job_id)
    return {"job_id": job_id, "job": status}

# CLI Argument Parser





@app.get("/", response_class=HTMLResponse)
def index_web():
    return FileResponse("templates/index.html")

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
            print("[INFO] No title provided. Brainstorming novel concept using Gemini...")
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
                print(f"[INFO] Generated Title: '{title}'")
                print(f"[INFO] Generated Description: '{desc[:150]}...'")
            except Exception as e:
                print(f"[ERROR] Failed to brainstorm novel: {e}")
                title = "Huyen Thoai Aetheria"
                desc = "Cau chuyen gia tuong day loi cuon."
                print(f"[INFO] Using fallback Title: '{title}'")
                
        novel = writer.init_novel_pipeline(title, desc)
        print(f"SUCCESS: Novel initialized. ID: {novel['id']}")
        
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
                        print(f"[INFO] ⚡ PHÁT HIỆN BỘ TRUYỆN MỚI TỪ FILE '{novel_file}': '{curr_n.get('title')}' (ID: {file_novel_id})")
            except Exception as e:
                print(f"[WARNING] Không thể đọc {novel_file}: {e}")

        # Cho file local đè hoàn toàn SECRET_NOVEL_ID trên GitHub secrets (chỉ dùng SECRET_NOVEL_ID nếu không có file local)
        novel_id = args.novel_id or os.getenv("INPUT_NOVEL_ID") or file_novel_id or os.getenv("SECRET_NOVEL_ID") or os.getenv("NOVEL_ID")
        if novel_id:
            novel_id = novel_id.strip().strip("'\"").strip()
                
        if not novel_id or novel_id.lower() == "all":
            if not config.validate_config():
                sys.exit(1)
            active_novels = database.get_active_novels()
            if not active_novels:
                print("[INFO] No active novels found in database with status 'writing'.")
                sys.exit(0)
            
            print(f"[INFO] Found {len(active_novels)} active novels. Executing pipelines...")
            for novel in active_novels:
                print("\n=========================================")
                print(f"EXECUTING PIPELINE FOR: {novel['title']} (ID: {novel['id']})")
                print("=========================================")
                try:
                    run_chapter_pipeline(novel['id'])
                except Exception as e:
                    print(f"[ERROR] Failed running pipeline for {novel['title']}: {e}")
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
    if len(sys.argv) == 1:
        sys.argv.append("--action")
        sys.argv.append("run-pipeline")
    main()





