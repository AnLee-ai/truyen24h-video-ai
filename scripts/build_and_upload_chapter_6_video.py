import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src import database, tts, video, telegram_uploader, config

CHAPTER_ID = "0f515321-1e70-4c3d-bdd1-8e13c011a8fa"
NOVEL_ID = "d1c402ea-4882-4ffa-81e5-639e93fed463"

def build_chapter_6():
    print(f"[INFO] 🚀 Đang khởi động tiến trình sản xuất & upload Video Tập 6 (ID: {CHAPTER_ID})...", flush=True)
    
    # 1. Lấy thông tin Tập 6 từ Supabase CSDL
    all_chapters = database.get_all_chapters(NOVEL_ID)
    ch6 = next((c for c in all_chapters if c.get("id") == CHAPTER_ID), None)
    if not ch6:
        print("[ERROR] Không tìm thấy Tập 6 trên Supabase CSDL!")
        return

    title = ch6.get("title", "Tập 6")
    content = ch6.get("content", "")
    print(f"[INFO] Tập 6: '{title}' ({len(content.split())} từ)...", flush=True)
    
    out_dir = os.path.join("output", CHAPTER_ID)
    os.makedirs(out_dir, exist_ok=True)
    
    # 2. Sinh âm thanh TTS Tiếng Việt 100%
    audio_path = os.path.join(config.OUTPUT_DIR, f"{CHAPTER_ID}_raw.mp3")
    srt_path = os.path.join(config.OUTPUT_DIR, f"{CHAPTER_ID}.srt")
    
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 10000:
        print("[INFO] Đang tổng hợp audio TTS Tiếng Việt cho Tập 6...", flush=True)
        # Sử dụng 3000 từ đầu tiên để tạo video 10-15 phút siêu nhanh
        audio_path, srt_path = tts.generate_voice_and_subs(text=content[:3500], chapter_id=CHAPTER_ID)

    # 3. Render Video 16:9 sắc nét (2-Pass Engine)
    out_video = os.path.join(out_dir, "video.mp4")
    print("[INFO] Đang render Video 16:9 sắc nét cho Tập 6...", flush=True)
    rendered_video = video.create_multi_image_slideshow_video(
        audio_path=audio_path,
        srt_path=srt_path,
        output_video_path=out_video,
        title=title
    )
    
    if rendered_video and os.path.exists(rendered_video):
        print(f"[SUCCESS] Render xong Video Tập 6 ({os.path.getsize(rendered_video)} bytes). Đang đẩy lên Supabase Storage CDN...", flush=True)
        
        # 4. Upload trực tiếp file MP4 lên Supabase Storage
        cdn_dest = f"videos/full/{CHAPTER_ID}_16_9.mp4"
        pub_url = database.upload_file_to_supabase(rendered_video, bucket_name="media", destination_path=cdn_dest)
        
        if pub_url:
            print("[SUCCESS] 🟢 ĐÃ UPLOAD THÀNH CÔNG VIDEO TẬP 6 LÊN SUPABASE CDN!", flush=True)
            print(f"🔗 LINK XEM VIDEO TRỰC TIẾP: {pub_url}", flush=True)
            
            # Khóa trạng thái hoàn thành Tập 6
            database.record_completed_chapter_local(CHAPTER_ID, 6)
            
            # Gửi bài đăng kèm link phát trực tiếp lên Telegram Channel
            caption = telegram_uploader.generate_seo_caption(6, title)
            excerpt = content[:500].strip() + "..."
            full_msg = f"{caption}\n\n📜 *Trích Đoạn Nội Dung:*\n\"{excerpt}\"\n\n🎬 *Link Phát Video HD (Supabase Direct CDN):*\n🔗 {pub_url}"
            telegram_uploader.send_progress_status_to_telegram(full_msg)
            print("[SUCCESS] 🟢 ĐÃ GỬI BÀI ĐĂNG TẬP 6 LÊN TELEGRAM CHANNEL!", flush=True)

if __name__ == "__main__":
    build_chapter_6()
