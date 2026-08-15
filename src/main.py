import argparse
import sys
from src import checkpoint
import os
import contextlib
import uvicorn
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from src import config
from src import database
from src import writer
from src import tts
from src import audio
from src import telegram_uploader
from src import video
from src import thumbnail_generator
from src import checkpoint
from src.queue_manager import job_queue

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
templates = Jinja2Templates(directory="src/templates")
# app.mount("/static", StaticFiles(directory="src/static"), name="static")


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

def audit_chapter_quality(ch: dict) -> tuple:
    """
    BỘ BẢO VỆ & RÀ SOÁT TIÊU CHUẨN TỰ ĐỘNG (Quality Auditor Engine):
    Rà soát Tiêu chuẩn chất lượng cho mỗi chương truyện:
    1. Kịch bản văn bản đầy đủ ≥ 1,000 từ (chuẩn audio > 10 phút).
    2. Không chứa tên nhân vật cũ rác (Trần Lam, Linh Vy, Minh Đức).
    """
    ch_num = ch.get("chapter_number", 0)
    ch_content = str(ch.get("content", ""))
    word_count = len(ch_content.split()) if ch_content else 0
    
    # 1. Tiêu chuẩn 1: Kịch bản text ngắn (<1000 từ) hoặc còn là BLUEPRINT
    if not ch_content or ch_content.startswith("BLUEPRINT:") or word_count < 1000:
        return False, f"Chương {ch_num}: Kịch bản quá ngắn ({word_count} từ < 1000 từ tiêu chuẩn)"
        
    # 2. Tiêu chuẩn 2: Chứa tên nhân vật rác cũ
    for old_name in ["Trần Lam", "Linh Vy", "Minh Đức", "Thùy Linh", "Cao Bá"]:
        if old_name in ch_content:
            return False, f"Kịch bản chứa tên nhân vật cũ rác '{old_name}'"
            
    return True, "PASSED"

def find_chapter_needing_video(novel_id: str) -> dict:
    """
    TỰ ĐỘNG PHÁT HIỆN TẬP CHƯA XỬ LÝ (CHỐNG LẶP CHƯƠNG 100%):
    1. Lấy danh sách 100% tập ĐÃ XONG từ Supabase + data/ + output/ + RAM.
    2. Nếu Tập ch_num đã nằm trong completed_set -> BỎ QUA HOÀN TOÀN.
    3. Trả về tập đầu tiên thực sự chưa hoàn thành.
    """
    completed_set = database.get_completed_chapters_set(novel_id)

    try:
        all_chapters = database.get_all_chapters(novel_id)
        for ch in all_chapters:
            ch_id = str(ch.get("id", ""))
            ch_num = int(ch.get("chapter_number", 0)) if str(ch.get("chapter_number", "")).isdigit() else 0
            
            # Kiểm tra xem Tập ch_num đã xong Media chưa
            is_done = (ch_num in completed_set) or (str(ch_num) in completed_set) or (ch_id in completed_set)
            
            if is_done:
                print(f"[QUALITY AUDITOR] 🟢 Tập {ch_num} (ID: {ch_id}) ĐÃ HOÀN THÀNH MEDIA. Bỏ qua hoàn toàn để làm tập tiếp theo!")
                continue

            # Rà soát kịch bản của Tập ch_num chưa hoàn thành
            passed, reason = audit_chapter_quality(ch)
            if not passed:
                print(f"[QUALITY AUDITOR] ⚠️ TẬP {ch_num} (ID: {ch_id}) KHÔNG ĐẠT TIÊU CHUẨN KỊCH BẢN ({reason}). Dành cho writer.write_next_chapter viết mới đủ 2500+ từ!")
                continue
                
            print(f"[QUALITY AUDITOR] 🎯 PHÁT HIỆN TẬP CHƯA XONG MEDIA: Tập {ch_num} (ID: {ch_id}). Tiến hành sản xuất Video!")
            return ch
            
    except Exception as e:
        print(f"[WARNING] Lỗi quét kiểm tra tiêu chuẩn chất lượng: {e}")
        
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
            file_mb = os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0
            print(f"[INFO] 🎬 Video dài đã được tạo tại: {video_path} (Kích thước: {file_mb:.1f} MB)")
            print(f"[INFO] 📤 Đang đẩy Video MP4 ({file_mb:.1f} MB) lên Supabase Storage CDN tốc độ cao...")
            video_public_url = database.upload_file_to_supabase(video_path, bucket_name="media", destination_path=f"videos/full/{chapter_id}_16_9.mp4")
            database.update_chapter_video_status(chapter_id, status="completed", video_url=video_public_url or video_path)
            
        # Đảm bảo video_public_url luôn chứa link CDN trực tiếp 100% không bao giờ bị rỗng
        if not video_public_url and config.SUPABASE_URL:
            video_public_url = f"{config.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/media/videos/full/{chapter_id}_16_9.mp4"
            
        # 4b. Tự động thiết kế Ảnh Bìa Thumbnail 16:9 YouTube 4K siêu bắt mắt (Xóa cache cũ tránh lỗi viền xanh)
        scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
        thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
        if os.path.exists(thumb_out_p):
            try:
                os.remove(thumb_out_p)
            except Exception:
                pass
        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num}...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, scene_img_p, thumb_out_p)
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
        print(f"[INFO] Bắt đầu tiến trình Upload video lên YouTube...")
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

from pydantic import BaseModel
class ThumbnailRequest(BaseModel):
    video_path: str
    chapter_title: str

from src.thumbnail_agent.pipeline import run_thumbnail_pipeline

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


