import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import database
from src.writer import safe_print

EPIC_TITLES = [
    "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận",
    "Thức Tỉnh Thần Thể, Nén Ép Thần Ma",
    "Huyết Mạch Thôn Thiên, Trấn Tám Phương",
    "Quyền Trấn Sơn Hà, Uy Chấn Chư Thiên",
    "Vô Địch Trùng Sinh, Hỗn Độn Luyện Khí",
    "Nghịch Thiên Độc Tôn, Luyện Hóa Thần Thạch",
    "Thôn Phệ Nguyên Khí, Phá Tam Cảnh",
    "Vạn Giới Quỳ Bái, Tiêu Viêm Xuất Thế",
    "Thôn Phệ Ma Nhẫn, Khai Mở Thần Thông",
    "Vô Song Kiếm Khí, Trảm Diệt Cường Địch",
    "Hệ Thống Thần Cấp, Thôn Phệ Vạn Vật",
    "Bá Thần Xuất Thế, Ngăn Cản Vạn Quân",
    "Thôn Phệ Vĩnh Hằng, Xây Dựng Đế Cơ",
    "Thôn Thiên Luyện Địa, Độc Tôn Vạn Cổ"
]

def fix_all_chapter_titles():
    safe_print("[INFO] Bắt đầu sửa toàn bộ tiêu đề bị trùng lặp 'Hành Trình Mới' trên CSDL Supabase...")
    try:
        client = database.get_client()
        # Query all chapters directly
        res = client.table("chapters").select("*").execute()
        chapters = res.data if res.data else []
        safe_print(f"[INFO] Tìm thấy {len(chapters)} chương trên CSDL Supabase.")
        
        for ch in chapters:
            ch_num = ch.get("chapter_number", 1)
            old_title = ch.get("title", "")
            if "Hành Trình Mới" in old_title or not old_title or old_title == f"Chương {ch_num}":
                epic_name = EPIC_TITLES[(ch_num - 1) % len(EPIC_TITLES)]
                new_title = f"{epic_name} (Tập {ch_num})"
                safe_print(f"[INFO] Cập nhật Tập {ch_num}: '{old_title}' -> '{new_title}'")
                try:
                    client.table("chapters").update({"title": new_title}).eq("id", ch["id"]).execute()
                except Exception as e:
                    safe_print(f"[WARNING] Lỗi cập nhật chapter {ch_num}: {e}")
        safe_print("[SUCCESS] 🟢 ĐÃ CẬP NHẬT 100% CÁC TIÊU ĐỀ CHƯƠNG ĐỘC ĐÁO & BẮT MẮT!")
    except Exception as e:
        safe_print(f"[ERROR] Sửa tiêu đề: {e}")

if __name__ == "__main__":
    fix_all_chapter_titles()
