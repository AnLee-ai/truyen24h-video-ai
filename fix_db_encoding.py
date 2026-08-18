import os
from src import database
import ftfy

def fix_db_encoding():
    print("[INFO] Bắt đầu sửa lỗi font trong Database...")
    try:
        # Get all active novels
        novels = database.get_active_novels()
        for novel in novels:
            novel_id = novel.get("id")
            if not novel_id: continue
            
            # Fix novel title
            old_title = novel.get("title", "")
            if old_title:
                new_title = ftfy.fix_text(old_title)
                # Sửa thêm lỗi do mã hóa nhiều lớp quá nát
                for _ in range(2):
                    new_title = ftfy.fix_text(new_title)
                if new_title != old_title:
                    print(f"[NOVEL] Fixed: {old_title} -> {new_title}")
                    database.get_client().table('novels').update({"title": new_title}).eq('id', novel_id).execute()
            
            # Fetch all chapters for this novel
            chapters = database.get_all_chapters(novel_id)
            for chapter in chapters:
                chap_id = chapter.get("id")
                chap_title = chapter.get("title", "")
                
                if chap_title and chap_id:
                    new_chap_title = ftfy.fix_text(chap_title)
                    # Sửa thêm lỗi do mã hóa nhiều lớp quá nát
                    for _ in range(2):
                        new_chap_title = ftfy.fix_text(new_chap_title)
                    
                    if new_chap_title != chap_title:
                        print(f"  [CHAP {chapter.get('chapter_number')}] Fixed: {chap_title} -> {new_chap_title}")
                        database.get_client().table('chapters').update({"title": new_chap_title}).eq('id', chap_id).execute()

        print("[SUCCESS] Đã sửa xong toàn bộ Database!")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    fix_db_encoding()