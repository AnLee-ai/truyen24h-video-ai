import os
import shutil
import json
from src import database, config

def main():
    print("[INFO] Bat dau don dep toan bo Cache & CSDL truyen cu...")
    
    # 1. Xoa sach thu muc output/ local
    output_dir = "output"
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                print(f"   - Da xoa cache local: {item_path}")
            except Exception as e:
                print(f"   - Khong the xoa {item_path}: {e}")
                
    # 2. Reset so tien do local data/chapters_progress.json
    progress_file = os.path.join("data", "chapters_progress.json")
    os.makedirs("data", exist_ok=True)
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump({"completed_chapters": [], "current_chapter": 1}, f, ensure_ascii=False, indent=2)
    print("   - Da reset data/chapters_progress.json ve Chuong 1.")

    # 3. Xoa cac tap cu khoi Supabase CSDL
    try:
        client = database.get_client()
        res = client.table("chapters").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"[SUCCESS] Da xoa sach toan bo tap cu khoi CSDL Supabase!")
    except Exception as err:
        print(f"[WARNING] Xoa CSDL Supabase canh bao: {err}")

    print("[SUCCESS] DA HOAN THANH 100% TAY SACH CACHE TRUYEN CU!")

if __name__ == "__main__":
    main()
