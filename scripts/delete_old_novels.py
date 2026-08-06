import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import database
from src.writer import safe_print

def purge_all_old_novels():
    safe_print("[INFO] Bắt đầu xóa sạch 100% tất cả bộ truyện cũ...")
    
    # 1. Xóa khỏi Supabase
    try:
        client = database.get_client()
        res = client.table("novels").select("*").execute()
        novels = res.data if res.data else []
        for n in novels:
            n_id = n.get("id")
            title = n.get("title", "")
            if "Vạn Cổ Thần Vương" not in title and n_id != "van-co-than-vuong-v1":
                safe_print(f"[INFO] Xóa bộ truyện cũ khỏi Supabase: '{title}' (ID: {n_id})...")
                try:
                    client.table("chapters").delete().eq("novel_id", n_id).execute()
                except Exception as e1:
                    safe_print(f"[WARNING] Lỗi xóa chapters: {e1}")
                try:
                    client.table("novels").delete().eq("id", n_id).execute()
                except Exception as e2:
                    safe_print(f"[WARNING] Lỗi xóa novel: {e2}")
    except Exception as e:
        safe_print(f"[INFO] Xóa trên Supabase: {e}")
        
    # 2. Xóa các file rác cũ trong thư mục output (giữ lại test)
    if os.path.exists("output"):
        for item in os.listdir("output"):
            item_path = os.path.join("output", item)
            if item == "test":
                continue
            if os.path.isdir(item_path):
                safe_print(f"[INFO] Xóa thư mục output cũ: {item_path}")
                shutil.rmtree(item_path, ignore_errors=True)
            elif item.endswith(".json") and item != "current_novel.json":
                safe_print(f"[INFO] Xóa file json cũ: {item_path}")
                try:
                    os.remove(item_path)
                except Exception:
                    pass

    # 3. Đảm bảo file data/active_novel.json duy nhất lưu Vạn Cổ Thần Vương
    new_novel_data = {
        "id": "van-co-than-vuong-v1",
        "title": "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận",
        "description": "Truyện tiên hiệp huyền huyễn cực kỳ kịch tính. Nam chính Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, từng bước luyện hóa vạn giới chư thiên, nén ép vạn giới thần ma, xây dựng lại trật tự vĩnh hằng.",
        "main_character": "Tiêu Viêm",
        "heroine": "Vân Vận",
        "status": "writing"
    }
    
    os.makedirs("data", exist_ok=True)
    import json
    with open("data/active_novel.json", "w", encoding="utf-8") as f:
        json.dump(new_novel_data, f, ensure_ascii=False, indent=2)
    with open("output/current_novel.json", "w", encoding="utf-8") as f:
        json.dump(new_novel_data, f, ensure_ascii=False, indent=2)

    safe_print("[SUCCESS] 🟢 ĐÃ XÓA SẠCH 100% CÁC BỘ TRUYỆN CŨ! CHỈ GIỮ LẠI BỘ TRUYỆN MỚI 'VẠN CỔ THẦN VƯƠNG'!")

if __name__ == "__main__":
    purge_all_old_novels()
