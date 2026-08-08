import os
import sys
import json
from src import database

def main():
    print("[INFO] Bat dau hop nhat va loai bo TRIET DE BÔ TRUYEN TRUNG LAP trong CSDL Supabase...")
    client = database.get_client()
    
    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    
    try:
        res = client.table("novels").select("*").eq("title", active_novel_title).order("created_at", desc=False).execute()
        if res.data and len(res.data) > 1:
            primary_novel = res.data[0] # Keep earliest created row: d1c402ea-4882-4ffa-81e5-639e93fed463
            primary_id = primary_novel["id"]
            duplicate_ids = [r["id"] for r in res.data[1:]]
            
            print(f"   - Phap hien {len(duplicate_ids)} bo truyen trùng lap! Giu lai primary novel_id: {primary_id}")
            
            for dup_id in duplicate_ids:
                # Chuyển tất cả child rows về primary_id
                for tbl in ["characters", "world_lore", "narrative_threads", "chapters"]:
                    try:
                        client.table(tbl).update({"novel_id": primary_id}).eq("novel_id", dup_id).execute()
                        print(f"     + Da chuyen du lieu bang '{tbl}' tu {dup_id} sang {primary_id}")
                    except Exception as e_t:
                        print(f"     - Chuyen du lieu bang '{tbl}' canh bao: {e_t}")
                
                # Xóa dòng novel trùng lặp
                try:
                    client.table("novels").delete().eq("id", dup_id).execute()
                    print(f"     [SUCCESS] Da xoa bo truyen trùng lap (ID: {dup_id})!")
                except Exception as e_d:
                    print(f"     - Xoa novel trùng lap (ID: {dup_id}) canh bao: {e_d}")
                    
            # Cập nhật file active_novel.json local với primary_id
            active_novel_data = {
                "id": primary_id,
                "title": active_novel_title,
                "description": primary_novel.get("description", ""),
                "status": "writing"
            }
            os.makedirs("data", exist_ok=True)
            with open("data/active_novel.json", "w", encoding="utf-8") as f:
                json.dump(active_novel_data, f, ensure_ascii=False, indent=2)
            print(f"   - Da dong bo file data/active_novel.json voi novel_id duy nhat ({primary_id}).")
        else:
            print("   - Khong con bo truyen trung lap nao trong bang 'novels'.")
    except Exception as e:
        print(f"   [NOVELS] Canh bao: {e}")

    print("[SUCCESS] DA HOAN THANH HOP NHAT BO TRUYEN DUY NHAT CHO SUPABASE!")

if __name__ == "__main__":
    main()
