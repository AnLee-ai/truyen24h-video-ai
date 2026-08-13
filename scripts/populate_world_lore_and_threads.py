from src import database

def main():
    print("[INFO] Bat dau nap du lieu World Lore & Narrative Threads vao CSDL Supabase...")
    client = database.get_client()
    
    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    active_world_name = "Đấu Khí Đại Lục / Vạn Cổ Thần Vương Universe"
    
    # 1. Lay active novel_id
    novel_id = None
    try:
        res = client.table("novels").select("*").eq("status", "writing").limit(1).execute()
        if res.data:
            novel_id = res.data[0]["id"]
            print(f"   - Lay duoc active novel_id: {novel_id}")
    except Exception as e:
        print(f"   - Query novel_id canh bao: {e}")
        
    if not novel_id:
        novel_id = "van-co-than-vuong-v1"

    # 2. Danh sach Du lieu World Lore (Boi Canh The Gioi)
    lore_entries = [
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "world_name": active_world_name,
            "keyword": "Đấu Khí Đại Lục",
            "description": "Thế giới tu luyện Đấu Khí hùng vĩ nơi cường giả làm tôn. Phân chia cảnh giới: Đấu Giả, Đấu Sư, Đại Đấu Sư, Đấu Linh, Đấu Vương, Đấu Hoàng, Đấu Tông, Đấu Tôn, Đấu Thánh, Đấu Đế."
        },
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "world_name": active_world_name,
            "keyword": "Hệ Thống Thôn Phệ Vô Tận",
            "description": "Bá đạo ngón tay vàng của Tiêu Viêm. Có khả năng thôn phệ vạn vật, luyện hóa thần ma, trích xuất căn cơ tu vi và dị hỏa của đối thủ để vô hạn đột phá."
        },
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "world_name": active_world_name,
            "keyword": "Vân Lam Tông",
            "description": "Tông môn Phong Hệ bá chủ tại Gia Mã Đế Quốc. Do Vân Vận làm Tông Chủ, phong cách tu luyện trường kiếm thanh cao và tốc độ bão táp."
        },
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "world_name": active_world_name,
            "keyword": "Dị Hỏa Vẫn Lạc",
            "description": "Loại ngọn lửa cuồng nổ xếp hạng trong Bảng Dị Hỏa Thượng Cổ. Tiêu Viêm dung hợp cùng Cốt Chưng U Hỏa của Dược Lão để nén ép kẻ thù."
        },
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "world_name": active_world_name,
            "keyword": "Hồn Điện",
            "description": "Thế lực sát thủ phản diện tà ác âm thầm săn lùng các linh hồn cường giả tôn giả chư thiên. Là kẻ thù truyền kiếp của Tiêu Viêm và Dược Lão."
        }
    ]

    for idx, lore in enumerate(lore_entries):
        try:
            client.table("world_lore").upsert(lore, on_conflict="novel_id,keyword").execute()
            print(f"   + Da nap World Lore #{idx+1}")
        except Exception:
            lore_base = {
                "novel_id": lore["novel_id"],
                "keyword": lore["keyword"],
                "description": lore["description"]
            }
            try:
                client.table("world_lore").upsert(lore_base, on_conflict="novel_id,keyword").execute()
                print(f"   + Da nap World Lore #{idx+1} (base)")
            except Exception as err:
                print(f"   - Nap World Lore #{idx+1} canh bao: {err}")

    # 3. Danh sach Du lieu Narrative Threads (Tuyến Truyện Kịch Tính)
    narrative_threads = [
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "thread_name": "Trùng Sinh Thôn Phệ & Đột Phá Đấu Đế",
            "description": "Tiêu Viêm trùng sinh kích hoạt Hệ Thống Thôn Phệ Vô Tận, từng bước càn quét kẻ thù, lật đổ áp chế của Hồn Điện và hướng tới cảnh giới Đấu Đế Thần Vương.",
            "status": "open"
        },
        {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "thread_name": "Định Mệnh Giữa Tiêu Viêm & Vân Vận",
            "description": "Mối duyên định mệnh giữa Nam chính Tiêu Viêm và Tông chủ Vân Vận từ Ma Thú Sơn Mạch đến trận chiến quy định Vân Lam Tông.",
            "status": "open"
        }
    ]

    for idx, thread in enumerate(narrative_threads):
        try:
            client.table("narrative_threads").upsert(thread, on_conflict="id").execute()
            print(f"   + Da nap Narrative Thread #{idx+1}")
        except Exception:
            thread_base = {
                "novel_id": thread["novel_id"],
                "thread_name": thread["thread_name"],
                "description": thread["description"],
                "status": thread["status"]
            }
            try:
                client.table("narrative_threads").upsert(thread_base, on_conflict="id").execute()
                print(f"   + Da nap Narrative Thread #{idx+1} (base)")
            except Exception as err:
                print(f"   - Nap Narrative Thread #{idx+1} canh bao: {err}")

    print("[SUCCESS] DA NAP THANH CONG TOAN BO DULIEU WORLD LORE & NARRATIVE THREADS VÀO SUPABASE!")

if __name__ == "__main__":
    main()
