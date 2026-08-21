        existing_chapter_numbers = {c["chapter_number"] for c in existing_chapters}
        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or f"Chương {ch_num}"
            blueprint_text = ch_data.get("blueprint") or "Tiếp tục diễn biến câu chuyện."
            
            if ch_num not in existing_chapter_numbers:
                ch_record = database.create_chapter(
                    novel_id=novel_id,
                    chapter_number=ch_num,
                    title=ch_title,
                    content=f"BLUEPRINT: {blueprint_text}"
                )
                if ch_record:
                    inserted_chapters.append(ch_record)
            
        print(f"[INFO] Created/Updated {len(inserted_chapters)} new chapter blueprints in DB.")
        return inserted_chapters
    except Exception as e:
        print(f"[ERROR] Failed to generate/parse blueprints for Arc {arc_num}: {e}")
        return []

