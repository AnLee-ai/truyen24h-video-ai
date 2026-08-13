import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src import database, writer

NOVEL_ID = "d1c402ea-4882-4ffa-81e5-639e93fed463"

def fix_all_chapters():
    print(f"[INFO] Cleaning legacy character names across all chapters in Supabase for novel {NOVEL_ID}...")
    client = database.get_client()
    chapters = database.get_all_chapters(NOVEL_ID)
    
    fixed_count = 0
    for ch in chapters:
        ch_id = ch.get("id")
        ch_num = ch.get("chapter_number")
        content = ch.get("content", "")
        title = ch.get("title", "")
        
        sanitized_content, was_modified_c = writer.verify_and_sanitize_chapter_content(content, NOVEL_ID)
        sanitized_title, was_modified_t = writer.verify_and_sanitize_chapter_content(title, NOVEL_ID)
        
        if was_modified_c or was_modified_t:
            print(f"[INFO] Updating Chapter {ch_num} (ID: {ch_id})...")
            client.table("chapters").update({
                "content": sanitized_content,
                "title": sanitized_title
            }).eq("id", ch_id).execute()
            fixed_count += 1
            
    print(f"[SUCCESS] Scanned {len(chapters)} chapters! Cleaned {fixed_count} chapters with legacy character names!")

if __name__ == "__main__":
    fix_all_chapters()
