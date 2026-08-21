import sys

def fix_file_again():
    with open('src/writer.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if '    else:\n' == line:
            # Check what's next
            if 'blueprint_text' in lines[i+1]:
                print("Fixing else block")
                lines.insert(i+1, '        existing_nums = [int(c["chapter_number"]) for c in all_chapters if str(c.get("chapter_number", "")).isdigit()] + list(all_done_nums)\n')
                lines.insert(i+2, '        next_ch_number = (max(existing_nums) + 1) if existing_nums else 1\n')
                lines.insert(i+3, '\n')
                lines.insert(i+4, '    print(f"[INFO] BẮT ĐẦU QUY TRÌNH VIẾT CHƯƠNG MỚI: Chương {next_ch_number} (Đã hoàn thành các tập: {sorted(list(all_done_nums))})...")\n')
                lines.insert(i+5, '    current_arc = get_current_arc(novel_id, next_ch_number)\n')
                lines.insert(i+6, '    chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)\n')
                lines.insert(i+7, '    if not chapter_record:\n')
                lines.insert(i+8, '        generate_arc_blueprints(novel_id, current_arc)\n')
                lines.insert(i+9, '        all_chapters = database.get_all_chapters(novel_id)\n')
                lines.insert(i+10, '        chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)\n')
                lines.insert(i+11, '    if not chapter_record:\n')
                lines.insert(i+12, '        chapter_record = database.create_chapter(novel_id=novel_id, chapter_number=next_ch_number, title=f"Chương {next_ch_number}", content=f"BLUEPRINT: Diễn biến tiếp theo.")\n')
                break

    with open('src/writer.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
fix_file_again()
