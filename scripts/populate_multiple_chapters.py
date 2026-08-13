from src import database

def main():
    print("[INFO] Bat dau tao va nap 5 Tap Truyen moi cho Van Co Than Vuong vao Supabase CSDL...")
    client = database.get_client()
    
    # 1. Lay primary novel_id
    novel_id = None
    try:
        res = client.table("novels").select("id").eq("status", "writing").limit(1).execute()
        if res.data:
            novel_id = res.data[0]["id"]
            print(f"   - Primary novel_id: {novel_id}")
    except Exception as e:
        print(f"   - Query novel_id canh bao: {e}")
        
    if not novel_id:
        novel_id = "d1c402ea-4882-4ffa-81e5-639e93fed463"

    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"

    # 2. Danh sach 5 Tap Truyen Tien Hiep Kich Tinh
    chapters_list = [
        {
            "chapter_number": 1,
            "title": "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận",
            "content": "Đấu Khí Đại Lục, Ô Thán Thành. Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, thề càn quét vạn giới chư thiên, lật đổ áp chế của Hồn Điện và Vân Lam Tông."
        },
        {
            "chapter_number": 2,
            "title": "Luyện Hóa Dị Hỏa, Đấu Khí Đột Phá",
            "content": "Dưới sự hướng dẫn của Dược Lão trong chiếc nhẫn cổ, Tiêu Viêm kích hoạt chức năng thôn phệ Dị Hỏa, luyện hóa Cốt Chưng U Hỏa, cuồng phong bão táp đột phá cảnh giới Đấu Vương."
        },
        {
            "chapter_number": 3,
            "title": "Ma Thú Sơn Mạch, Kỳ Ngộ Vân Vận",
            "content": "Tiêu Viêm tiến vào Ma Thú Sơn Mạch rèn luyện, tình cờ cứu nguy cho Tông chủ Vân Lam Tông Vân Vận đang bị Ma Thú Cổ Thượng Cổ vây hãm, mối định mệnh kỳ ngộ bắt đầu."
        },
        {
            "chapter_number": 4,
            "title": "Hệ Thống Thôn Phệ, Nén Ép Cường Địch",
            "content": "Cường giả Hồn Điện thâm nhập Gia Mã Đế Quốc âm mưu bắt giữ Dược Lão. Tiêu Viêm vận dụng chiêu thức Thôn Phệ Vạn Giới, nuốt chửng linh hồn phản diện, uy chấn bối cảnh Tiên Hiệp."
        },
        {
            "chapter_number": 5,
            "title": "Đấu Đế Thần Vương, Vĩnh Hằng Bá Chủ",
            "content": "Tiêu Viêm tập hợp 24 loại Dị Hỏa Thượng Cổ, vượt qua kiếp nạn Ma Thú Sơn Mạch và Vân Lam Tông, mở ra kỷ nguyên bá chủ Đấu Đế Thần Vương xé tan hư không."
        }
    ]

    for ch in chapters_list:
        data = {
            "novel_id": novel_id,
            "novel_title": active_novel_title,
            "chapter_number": ch["chapter_number"],
            "title": ch["title"],
            "content": ch["content"]
        }
        try:
            existing = client.table("chapters").select("id").eq("novel_id", novel_id).eq("chapter_number", ch["chapter_number"]).execute()
            if existing.data and len(existing.data) > 0:
                c_id = existing.data[0]["id"]
                try:
                    client.table("chapters").update(data).eq("id", c_id).execute()
                    print(f"   + Da cap nhat Chapter #{ch['chapter_number']}")
                except Exception:
                    data.pop("novel_title", None)
                    client.table("chapters").update(data).eq("id", c_id).execute()
                    print(f"   + Da cap nhat Chapter #{ch['chapter_number']} (base)")
            else:
                try:
                    client.table("chapters").insert(data).execute()
                    print(f"   + Da tao moi Chapter #{ch['chapter_number']}")
                except Exception:
                    data.pop("novel_title", None)
                    client.table("chapters").insert(data).execute()
                    print(f"   + Da tao moi Chapter #{ch['chapter_number']} (base)")
        except Exception as e:
            print(f"   - Thao tac Chapter #{ch['chapter_number']} canh bao: {e}")

    print("[SUCCESS] DA NAP THANH CONG 5 TAP TRUYEN VAO BANG CHAPTERS SUPABASE!")

if __name__ == "__main__":
    main()
