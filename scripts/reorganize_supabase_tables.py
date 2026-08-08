import os
import sys
import json
from src import database, config

def main():
    print("[INFO] Bat dau dung va sap xep lai toan bo CSDL Supabase...")
    client = database.get_client()
    
    # 1. Dam bao Bo Truyen duy nhat 'Van Co Than Vuong' duoc ghi nhan status = 'writing'
    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    active_novel_desc = "Truyện tiên hiệp huyền huyễn cực kỳ kịch tính. Nam chính Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, từng bước luyện hóa vạn giới chư thiên, nén ép vạn giới thần ma, xây dựng lại trật tự vĩnh hằng."
    
    # Chuyển tất cả bộ truyện cũ sang status 'archived'
    try:
        client.table("novels").update({"status": "archived"}).neq("title", active_novel_title).execute()
        print("   - Da chuyen tat ca cac bo truyen cu sang status 'archived'")
    except Exception as e:
        print(f"   - Cap nhat status novels cu canh bao: {e}")
        
    # Lấy hoặc tạo mới active novel
    novel_id = None
    try:
        res = client.table("novels").select("*").eq("title", active_novel_title).execute()
        if res.data:
            novel_id = res.data[0]["id"]
            client.table("novels").update({"status": "writing", "description": active_novel_desc}).eq("id", novel_id).execute()
            print(f"   - Da cap nhat active novel (ID: {novel_id}) status = 'writing'")
        else:
            ins_res = client.table("novels").insert({
                "title": active_novel_title,
                "description": active_novel_desc,
                "status": "writing"
            }).execute()
            if ins_res.data:
                novel_id = ins_res.data[0]["id"]
                print(f"   - Da tao moi active novel (ID: {novel_id})")
    except Exception as e:
        print(f"   - Loi thao tac novels table: {e}")

    if not novel_id:
        novel_id = "van-co-than-vuong-v1"

    # 2. Xoa sach 100% nhan vat cu khoi bang 'characters'
    try:
        client.table("characters").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("   - Da xoa sach toan bo nhan vat cu khoi bang 'characters'")
    except Exception as e:
        print(f"   - Xoa characters cu canh bao: {e}")

    # 3. Them 4 Nhan Vat Chu Chot cho 'Van Co Than Vuong'
    fresh_characters = [
        {
            "novel_id": novel_id,
            "name": "Tiêu Viêm",
            "description": "Nam chính trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận. Mặc trường bào xanh thẫm, tóc đen sắc bén, cầm hỏa kiếm tím huyền thoại.",
            "power_tier": "Bá Chủ Trùng Sinh",
            "combat_stats": {"level": "Đấu Vương / Thôn Phệ Giả", "element": "Dị Hỏa Vẫn Lạc"},
            "relationships": {"sư_phụ": "Dược Lão", "nữ_chính": "Vân Vận"}
        },
        {
            "novel_id": novel_id,
            "name": "Vân Vận",
            "description": "Nữ chính Tông chủ Vân Lam Tông. Khí chất thanh cao kiều diễm, mặc váy lụa xanh ngọc, sử dụng trường kiếm phong hệ sắc bén.",
            "power_tier": "Tông Chủ Vân Lam Tông",
            "combat_stats": {"level": "Đấu Hoàng Phong Hệ", "weapon": "Phong Linh Kiếm"},
            "relationships": {"bằng_hữu": "Tiêu Viêm"}
        },
        {
            "novel_id": novel_id,
            "name": "Dược Lão",
            "description": "Sư phụ tôn giả thượng cổ. Linh hồn thể bạch y uy nghiêm, làm chủ Cốt Chưng U Hỏa, luyện dược sư đệ nhất chư thiên.",
            "power_tier": "Dược Tôn Giả",
            "combat_stats": {"level": "Đấu Tôn Linh Hồn", "flame": "Cốt Chưng U Hỏa"},
            "relationships": {"đồ_đệ": "Tiêu Viêm"}
        },
        {
            "novel_id": novel_id,
            "name": "Huân Nhi",
            "description": "Thiếu nữ thần bí gia tộc cổ đại. Dịu dàng thông tuệ, mặc váy tím trang nhã, sở hữu Đế Tộc Huyết Mạch tôn quý.",
            "power_tier": "Cổ Tộc Thiếu Nữ",
            "combat_stats": {"level": "Đấu Linh Cổ Tộc", "bloodline": "Đế Tộc Huyết Mạch"},
            "relationships": {"thanh_mai_trúc_mã": "Tiêu Viêm"}
        }
    ]

    for idx_c, char in enumerate(fresh_characters):
        try:
            client.table("characters").insert(char).execute()
            print(f"   + Da khoi tao nhan vat moi #{idx_c + 1}")
        except Exception as e:
            print(f"   - Insert nhan vat #{idx_c + 1} canh bao: {e}")

    # 4. Dong bo file active_novel.json local
    active_novel_data = {
        "id": novel_id,
        "title": active_novel_title,
        "description": active_novel_desc,
        "status": "writing"
    }
    os.makedirs("data", exist_ok=True)
    with open("data/active_novel.json", "w", encoding="utf-8") as f:
        json.dump(active_novel_data, f, ensure_ascii=False, indent=2)
    print("   - Da cap nhat file data/active_novel.json local muot ma.")

    print("[SUCCESS] DA HOAN THANH 100% QUY TRINH REORGANIZE CSDL SUPABASE!")

if __name__ == "__main__":
    main()
