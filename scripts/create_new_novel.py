import os
import sys
import json
import uuid

# Đảm bảo import src module chuẩn
sys.path.insert(0, os.path.abspath("."))

# Đảm bảo UTF-8 cho Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src import database, writer

def create_brand_new_novel(genre: str = "Tuyên Hiệp / Huyền Huyễn"):
    """Tự động sáng tác 1 bộ truyện mới 100% bằng InkOS Multi-Agent Engine."""
    print("=======================================================")
    print(" 📖 KHỞI TẠO BỘ TRUYỆN MỚI BẰNG INKOS MULTI-AGENT ENGINE")
    print("=======================================================\n")
    
    prompt = (
        "Bạn là InkOS Lead Writer AI. Hãy sáng tác 1 bộ truyện tiên hiệp/huyền huyễn độc đáo, cực kỳ kịch tính, hấp dẫn người đọc ngay từ chương đầu.\n"
        "Hãy xuất ra định dạng JSON với các thông tin sau:\n"
        "{\n"
        '  "title": "Tên Bộ Truyện Cực Hay (VD: Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận)",\n'
        '  "description": "Tóm tắt cốt truyện kịch tính (150-200 từ)",\n'
        '  "main_character": "Tên và xuất thân nam chính",\n'
        '  "heroine": "Tên và thế lực nữ chính",\n'
        '  "setting": "Bối cảnh thế giới tu tiên/huyền ảo"\n'
        "}\n"
        "Chỉ xuất duy nhất JSON."
    )
    
    res = writer.call_gemini(prompt, json_mode=True)
    data = writer.safe_loads(res)
    
    title = data.get("title") or "Vạn Cổ Thần Vương: Thôn Phệ Vô Tận"
    desc = data.get("description") or "Truyện tiên hiệp huyền huyễn kịch tính về hành trình trùng sinh nén ép vạn giới."
    
    print(f"📌 TÊN BỘ TRUYỆN MỚI: {title}")
    print(f"📝 BỐI CẢNH & TÓM TẮT: {desc[:200]}...\n")
    
    # Lưu vào CSDL Supabase hoặc CSDL Cục bộ nếu Supabase RLS bật
    novel_id = str(uuid.uuid4())
    try:
        n_rec = database.init_novel(title, desc)
        if n_rec and n_rec.get("id"):
            novel_id = n_rec["id"]
            print(f"[SUCCESS] Đã khởi tạo bộ truyện mới thành công trong Supabase DB (ID: {novel_id})!")
    except Exception:
        print(f"[INFO] Supabase RLS active. Khởi tạo bộ truyện mới cục bộ (ID: {novel_id}).")
        
    local_info = {
        "id": novel_id,
        "title": title,
        "description": desc,
        "main_character": data.get("main_character", "Tiêu Viêm"),
        "heroine": data.get("heroine", "Vân Vận"),
        "status": "writing"
    }
    
    os.makedirs("output", exist_ok=True)
    with open("output/current_novel.json", "w", encoding="utf-8") as f:
        json.dump(local_info, f, ensure_ascii=False, indent=2)
        
    print(f"[SUCCESS] Bộ truyện mới '{title}' đã sẵn sàng bắt đầu viết Chương 1!")
    return local_info

if __name__ == "__main__":
    create_brand_new_novel()
