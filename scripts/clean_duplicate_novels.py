import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src import database

MASTER_NOVEL_ID = "d1c402ea-4882-4ffa-81e5-639e93fed463"

def cleanup_duplicates():
    print("[INFO] Scanning Supabase 'novels' table to delete duplicate rows...")
    client = database.get_client()
    
    res = client.table("novels").select("*").execute()
    novels = res.data or []
    print(f"[INFO] Found {len(novels)} total novel rows in Supabase.")
    
    for n in novels:
        n_id = n.get("id")
        n_title = n.get("title")
        n_created = n.get("created_at")
        print(f"  - Novel Row: ID={n_id} | Title='{n_title}' | Created={n_created}")
        
        if n_id != MASTER_NOVEL_ID:
            print(f"  [DELETE] Removing duplicate novel row ID: {n_id}...")
            # Reassign any chapters under duplicate ID to MASTER_NOVEL_ID
            try:
                client.table("chapters").update({"novel_id": MASTER_NOVEL_ID}).eq("novel_id", n_id).execute()
            except Exception:
                pass
            # Delete duplicate novel row
            client.table("novels").delete().eq("id", n_id).execute()
            print(f"  [SUCCESS] Deleted duplicate novel row {n_id}!")
            
    print(f"[SUCCESS] CLEANUP COMPLETE! Only Master Novel {MASTER_NOVEL_ID} remains in Supabase CSDL!")

if __name__ == "__main__":
    cleanup_duplicates()
