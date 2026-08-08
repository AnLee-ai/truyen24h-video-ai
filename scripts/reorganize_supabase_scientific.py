import os
import json
from src import database

def main():
    print("[INFO] Bat dau quy trinh DONG BO & SAP XEP KHOA HOC 100% CSDL SUPABASE...")
    client = database.get_client()
    
    primary_novel_id = "d1c402ea-4882-4ffa-81e5-639e93fed463"
    novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    world_name = "Đấu Khí Đại Lục / Vạn Cổ Thần Vương Universe"
    novel_desc = "Truyện tiên hiệp huyền huyễn cực kỳ kịch tính. Nam chính Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, từng bước luyện hóa vạn giới chư thiên, nén ép vạn giới thần ma, xây dựng lại trật tự vĩnh hằng."

    # 1. DỌN DẸP SẠCH TẤT CẢ DỮ LIỆU CŨ VÀ TRÙNG LẶP NẾU CÓ
    print("   [1/6 NOVELS] Chuan hoa bang 'novels'...")
    try:
        # Xóa tất cả novel khác primary_novel_id
        client.table("novels").delete().neq("id", primary_novel_id).execute()
    except Exception as e:
        print(f"   - Clean novels warning: {e}")
        
    # Upsert novel chuẩn duy nhất
    novel_payload = {
        "id": primary_novel_id,
        "title": novel_title,
        "description": novel_desc,
        "status": "writing"
    }
    try:
        client.table("novels").upsert(novel_payload, on_conflict="id").execute()
        print(f"   [SUCCESS] Da cap nhat duy nhat 1 Novel record (ID: {primary_novel_id})")
    except Exception as e:
        print(f"   - Upsert novel error: {e}")

    # 2. CHUẨN HÓA BẢNG CHARACTERS (Phân chia vai trò rõ ràng)
    print("   [2/6 CHARACTERS] Chuan hoa bang 'characters'...")
    try:
        client.table("characters").delete().eq("novel_id", primary_novel_id).execute()
        client.table("characters").delete().neq("novel_id", primary_novel_id).execute()
    except Exception as e:
        print(f"   - Clean characters warning: {e}")

    structured_characters = [
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "name": "Tiêu Viêm",
            "description": "Nam chính trùng sinh mang Hệ Thống Thôn Phệ Vô Tận. Tóc đen sắc bén, mặc trường bào xanh thẫm, tay cầm hỏa kiếm tím huyền thoại.",
            "power_tier": "Bá Chủ Trùng Sinh (Đấu Vương)",
            "combat_stats": {"level": "Đấu Vương / Thôn Phệ Giả", "element": "Dị Hỏa Vẫn Lạc"},
            "relationships": {"sư_phụ": "Dược Lão", "nữ_chính": "Vân Vận"}
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "name": "Vân Vận",
            "description": "Nữ chính Tông chủ Vân Lam Tông. Khí chất thanh cao kiều diễm, mặc váy lụa xanh ngọc, sử dụng Phong Linh Kiếm sắc bén.",
            "power_tier": "Tông Chủ Vân Lam Tông (Đấu Hoàng)",
            "combat_stats": {"level": "Đấu Hoàng Phong Hệ", "weapon": "Phong Linh Kiếm"},
            "relationships": {"bằng_hữu": "Tiêu Viêm"}
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "name": "Dược Lão",
            "description": "Sư phụ tôn giả thượng cổ. Linh hồn thể bạch y uy nghiêm, làm chủ Cốt Chưng U Hỏa, luyện dược sư đệ nhất chư thiên.",
            "power_tier": "Dược Tôn Giả (Đấu Tôn)",
            "combat_stats": {"level": "Đấu Tôn Linh Hồn", "flame": "Cốt Chưng U Hỏa"},
            "relationships": {"đồ_đệ": "Tiêu Viêm"}
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "name": "Huân Nhi",
            "description": "Thiếu nữ thần bí gia tộc cổ đại. Dịu dàng thông tuệ, mặc váy tím trang nhã, sở hữu Đế Tộc Huyết Mạch tôn quý.",
            "power_tier": "Cổ Tộc Thiếu Nữ (Đấu Linh)",
            "combat_stats": {"level": "Đấu Linh Cổ Tộc", "bloodline": "Đế Tộc Huyết Mạch"},
            "relationships": {"thanh_mai_trúc_mã": "Tiêu Viêm"}
        }
    ]

    for idx, char in enumerate(structured_characters):
        try:
            client.table("characters").insert(char).execute()
            print(f"   + Da khoi tao Nhan Vat #{idx+1}")
        except Exception:
            char.pop("novel_title", None)
            char.pop("world_name", None)
            client.table("characters").insert(char).execute()
            print(f"   + Da khoi tao Nhan Vat #{idx+1} (base)")

    # 3. CHUẨN HÓA BẢNG WORLD_LORE (Phân loại bối cảnh khoa học)
    print("   [3/6 WORLD_LORE] Chuan hoa bang 'world_lore'...")
    try:
        client.table("world_lore").delete().eq("novel_id", primary_novel_id).execute()
        client.table("world_lore").delete().neq("novel_id", primary_novel_id).execute()
    except Exception as e:
        print(f"   - Clean world_lore warning: {e}")

    structured_lore = [
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "keyword": "Đấu Khí Đại Lục",
            "description": "[Cảnh Giới Tu Luyện] Thế giới tu luyện Đấu Khí hùng vĩ nơi cường giả làm tôn. Phân chia cảnh giới: Đấu Giả, Đấu Sư, Đại Đấu Sư, Đấu Linh, Đấu Vương, Đấu Hoàng, Đấu Tông, Đấu Tôn, Đấu Thánh, Đấu Đế."
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "keyword": "Hệ Thống Thôn Phệ Vô Tận",
            "description": "[Bá Đạo Ngón Tay Vàng] Hệ thống độc quyền của Tiêu Viêm. Có khả năng thôn phệ vạn vật, luyện hóa thần ma, trích xuất căn cơ tu vi và dị hỏa của đối thủ để vô hạn đột phá."
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "keyword": "Vân Lam Tông",
            "description": "[Tông Môn Bá Chủ] Tông môn Phong Hệ lớn nhất Gia Mã Đế Quốc do Vân Vận làm Tông Chủ. Phong cách tu luyện trường kiếm thanh cao và tốc độ bão táp."
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "keyword": "Dị Hỏa Vẫn Lạc",
            "description": "[Bảo Vật Thượng Cổ] Loại ngọn lửa cuồng nổ xếp hạng trong Bảng Dị Hỏa Thượng Cổ. Tiêu Viêm dung hợp cùng Cốt Chưng U Hỏa của Dược Lão để nén ép kẻ thù."
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "world_name": world_name,
            "keyword": "Hồn Điện",
            "description": "[Thế Lực Phản Diện] Tổ chức sát thủ tà ác âm thầm săn lùng các linh hồn cường giả tôn giả chư thiên. Kẻ thù truyền kiếp của Tiêu Viêm và Dược Lão."
        }
    ]

    for idx, lore in enumerate(structured_lore):
        try:
            client.table("world_lore").insert(lore).execute()
            print(f"   + Da khoi tao Boi Canh #{idx+1}")
        except Exception:
            lore.pop("novel_title", None)
            lore.pop("world_name", None)
            client.table("world_lore").insert(lore).execute()
            print(f"   + Da khoi tao Boi Canh #{idx+1} (base)")

    # 4. CHUẨN HÓA BẢNG NARRATIVE_THREADS (Tuyến truyện mạch lạc)
    print("   [4/6 NARRATIVE_THREADS] Chuan hoa bang 'narrative_threads'...")
    try:
        client.table("narrative_threads").delete().eq("novel_id", primary_novel_id).execute()
        client.table("narrative_threads").delete().neq("novel_id", primary_novel_id).execute()
    except Exception as e:
        print(f"   - Clean narrative_threads warning: {e}")

    structured_threads = [
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "thread_name": "Arc 1: Trùng Sinh Thôn Phệ & Khởi Đầu Ô Thán Thành",
            "description": "Tiêu Viêm trùng sinh kích hoạt Hệ Thống Thôn Phệ Vô Tận tại Ô Thán Thành, luyện hóa Cốt Chưng U Hỏa cùng Dược Lão và càn quét kẻ thù.",
            "status": "open"
        },
        {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "thread_name": "Arc 2: Ma Thú Sơn Mạch & Định Mệnh Với Vân Vận",
            "description": "Tiêu Viêm rèn luyện tại Ma Thú Sơn Mạch, giải cứu Tông chủ Vân Lam Tông Vân Vận và đối đầu với áp chế của Hồn Điện.",
            "status": "open"
        }
    ]

    for idx, thread in enumerate(structured_threads):
        try:
            client.table("narrative_threads").insert(thread).execute()
            print(f"   + Da khoi tao Tuyen Truyen #{idx+1}")
        except Exception:
            thread.pop("novel_title", None)
            client.table("narrative_threads").insert(thread).execute()
            print(f"   + Da khoi tao Tuyen Truyen #{idx+1} (base)")

    # 5. CHUẨN HÓA BẢNG CHAPTERS (Nạp 5 Tập Nối Tiếp Ngăn Nắp)
    print("   [5/6 CHAPTERS] Chuan hoa bang 'chapters'...")
    try:
        client.table("chapters").delete().eq("novel_id", primary_novel_id).execute()
        client.table("chapters").delete().neq("novel_id", primary_novel_id).execute()
    except Exception as e:
        print(f"   - Clean chapters warning: {e}")

    structured_chapters = [
        {"chapter_number": 1, "title": "Tập 1: Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận", "content": "Đấu Khí Đại Lục, Ô Thán Thành. Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, thề càn quét vạn giới chư thiên, lật đổ áp chế của Hồn Điện và Vân Lam Tông."},
        {"chapter_number": 2, "title": "Tập 2: Luyện Hóa Dị Hỏa, Đấu Khí Đột Phá", "content": "Dưới sự hướng dẫn của Dược Lão trong chiếc nhẫn cổ, Tiêu Viêm kích hoạt chức năng thôn phệ Dị Hỏa, luyện hóa Cốt Chưng U Hỏa, cuồng phong bão táp đột phá cảnh giới Đấu Vương."},
        {"chapter_number": 3, "title": "Tập 3: Ma Thú Sơn Mạch, Kỳ Ngộ Vân Vận", "content": "Tiêu Viêm tiến vào Ma Thú Sơn Mạch rèn luyện, tình cờ cứu nguy cho Tông chủ Vân Lam Tông Vân Vận đang bị Ma Thú Cổ Thượng Cổ vây hãm, mối định mệnh kỳ ngộ bắt đầu."},
        {"chapter_number": 4, "title": "Tập 4: Hệ Thống Thôn Phệ, Nén Ép Cường Địch", "content": "Cường giả Hồn Điện thâm nhập Gia Mã Đế Quốc âm mưu bắt giữ Dược Lão. Tiêu Viêm vận dụng chiêu thức Thôn Phệ Vạn Giới, nuốt chửng linh hồn phản diện, uy chấn bối cảnh Tiên Hiệp."},
        {"chapter_number": 5, "title": "Tập 5: Đấu Đế Thần Vương, Vĩnh Hằng Bá Chủ", "content": "Tiêu Viêm tập hợp 24 loại Dị Hỏa Thượng Cổ, vượt qua kiếp nạn Ma Thú Sơn Mạch và Vân Lam Tông, mở ra kỷ nguyên bá chủ Đấu Đế Thần Vương xé tan hư không."}
    ]

    ch1_id = None
    for ch in structured_chapters:
        ch_payload = {
            "novel_id": primary_novel_id,
            "novel_title": novel_title,
            "chapter_number": ch["chapter_number"],
            "title": ch["title"],
            "content": ch["content"]
        }
        try:
            res_c = client.table("chapters").insert(ch_payload).execute()
            if res_c.data and ch["chapter_number"] == 1:
                ch1_id = res_c.data[0]["id"]
            print(f"   + Da khoi tao Chapter #{ch['chapter_number']}")
        except Exception:
            ch_payload.pop("novel_title", None)
            res_c = client.table("chapters").insert(ch_payload).execute()
            if res_c.data and ch["chapter_number"] == 1:
                ch1_id = res_c.data[0]["id"]
            print(f"   + Da khoi tao Chapter #{ch['chapter_number']} (base)")

    # 6. CHUẨN HÓA BẢNG EPISODES_SUMMARY
    print("   [6/6 EPISODES_SUMMARY] Chuan hoa bang 'episodes_summary'...")
    try:
        client.table("episodes_summary").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    except Exception as e:
        print(f"   - Clean episodes_summary warning: {e}")

    if ch1_id:
        try:
            client.table("episodes_summary").insert({
                "chapter_id": ch1_id,
                "event_summary": "Tiêu Viêm trùng sinh tại Ô Thán Thành kích hoạt Hệ Thống Thôn Phệ Vô Tận, nén ép kẻ thù và bắt đầu hành trình bá chủ chư thiên."
            }).execute()
            print("   + Da khoi tao Episode 1 Summary thanh cong!")
        except Exception as e:
            print(f"   - Episodes summary insert warning: {e}")

    # Đồng bộ active_novel.json local
    os.makedirs("data", exist_ok=True)
    with open("data/active_novel.json", "w", encoding="utf-8") as f:
        json.dump({"id": primary_novel_id, "title": novel_title, "description": novel_desc, "status": "writing"}, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] DA SAP XEP HOAN HAO KHOA HOC 100% CSDL SUPABASE CHUAN TOAN DIEN!")

if __name__ == "__main__":
    main()
