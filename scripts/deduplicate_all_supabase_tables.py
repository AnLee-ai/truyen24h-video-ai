import os
import sys
import json
from src import database

def main():
    print("[INFO] Bat dau quat va loai bo TRIET DE TOAN BO TRUNG LAP trong CSDL Supabase...")
    client = database.get_client()
    
    # 1. Deduplicate bang 'characters' theo name
    try:
        chars_res = client.table("characters").select("id, name").execute()
        if chars_res.data:
            seen_names = set()
            deleted_count = 0
            for row in chars_res.data:
                name = row.get("name")
                if name in seen_names:
                    client.table("characters").delete().eq("id", row["id"]).execute()
                    deleted_count += 1
                else:
                    seen_names.add(name)
            print(f"   [CHARACTERS] Da xoa {deleted_count} nhan vat trung lap. Con lai {len(seen_names)} nhan vat duy nhat!")
    except Exception as e:
        print(f"   [CHARACTERS] Canh bao: {e}")

    # 2. Deduplicate bang 'world_lore' theo keyword
    try:
        lore_res = client.table("world_lore").select("id, keyword").execute()
        if lore_res.data:
            seen_lore = set()
            deleted_count = 0
            for row in lore_res.data:
                kw = row.get("keyword")
                if kw in seen_lore:
                    client.table("world_lore").delete().eq("id", row["id"]).execute()
                    deleted_count += 1
                else:
                    seen_lore.add(kw)
            print(f"   [WORLD_LORE] Da xoa {deleted_count} lore trung lap. Con lai {len(seen_lore)} lore duy nhat!")
    except Exception as e:
        print(f"   [WORLD_LORE] Canh bao: {e}")

    # 3. Deduplicate bang 'narrative_threads' theo thread_name
    try:
        thread_res = client.table("narrative_threads").select("id, thread_name").execute()
        if thread_res.data:
            seen_threads = set()
            deleted_count = 0
            for row in thread_res.data:
                tn = (row.get("thread_name") or "").strip()
                if tn in seen_threads:
                    client.table("narrative_threads").delete().eq("id", row["id"]).execute()
                    deleted_count += 1
                else:
                    seen_threads.add(tn)
            print(f"   [NARRATIVE_THREADS] Da xoa {deleted_count} thread trung lap. Con lai {len(seen_threads)} thread duy nhat!")
    except Exception as e:
        print(f"   [NARRATIVE_THREADS] Canh bao: {e}")

    print("[SUCCESS] DA HOAN THANH DEDUP LAM SACH 100% CSDL SUPABASE!")

if __name__ == "__main__":
    main()
