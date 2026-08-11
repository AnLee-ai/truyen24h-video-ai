import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src import database, telegram_uploader, config

NOVEL_ID = "d1c402ea-4882-4ffa-81e5-639e93fed463"

def dispatch_all_short_chapters_to_telegram():
    print(f"[INFO] 🚀 Bắt đầu gửi toàn bộ kịch bản & Link CDN của Tập 1 đến Tập 5 lên kênh Telegram...", flush=True)
    all_chapters = database.get_all_chapters(NOVEL_ID)
    target_chapters = [c for c in all_chapters if c.get("chapter_number") in [1, 2, 3, 4, 5]]
    target_chapters.sort(key=lambda x: x.get("chapter_number"))

    for ch in target_chapters:
        ch_num = ch.get("chapter_number")
        ch_id = ch.get("id")
        title = ch.get("title", f"Tập {ch_num}")
        content = ch.get("content", "")
        
        print(f"\n[INFO] 🎙️ ĐANG GỬI TẬP {ch_num}: {title} (Độ dài: {len(content.split())} từ)...", flush=True)
        
        # 1. Tạo SEO Caption Telegram đầy đủ
        caption = telegram_uploader.generate_seo_caption(ch_num, title)
        
        # 2. Tạo đường link Supabase Storage CDN trực tiếp chuẩn
        supabase_base = (config.SUPABASE_URL or "").rstrip('/')
        cdn_url = f"{supabase_base}/storage/v1/object/public/media/videos/full/{ch_id}_16_9.mp4"
        
        # 3. Trích đoạn kịch bản hay nhất
        excerpt = content[:600].strip() + "..."
        
        # 4. Tạo nội dung bài viết Telegram hoàn chỉnh
        full_msg = (
            f"{caption}\n\n"
            f"📜 *Trích Đoạn Nội Dung:*\n\"{excerpt}\"\n\n"
            f"🎬 *Link Phát Video HD (Supabase Direct CDN):*\n🔗 {cdn_url}"
        )
        
        # 5. Gửi lên Telegram Channel
        ok = telegram_uploader.send_progress_status_to_telegram(full_msg)
        if ok:
            print(f"[SUCCESS] 🟢 ĐÃ GỬI THÀNH CÔNG BÀI VIẾT TẬP {ch_num} LÊN TELEGRAM!", flush=True)
        else:
            print(f"[WARNING] Không thể gửi bài viết Tập {ch_num} lên Telegram.", flush=True)

if __name__ == "__main__":
    dispatch_all_short_chapters_to_telegram()


