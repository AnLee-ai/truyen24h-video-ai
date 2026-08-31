import re

with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_memory = '''previous_chapters = [c for c in all_chapters if c["chapter_number"] < next_ch_number and not str(c.get("content", "")).startswith("BLUEPRINT:")]
    
    # 1. Extract forbidden phrases (anti-repetition)
    forbidden_phrases_list = []
    for ch in previous_chapters[-3:]:
        ch_content = str(ch.get('content', ''))
        words = ch_content.split()[:50]
        if words:
            forbidden_phrases_list.append(" ".join(words))
    forbidden_phrases = "\\n- ".join(forbidden_phrases_list) if forbidden_phrases_list else "Không có"

    # 2. Smart Continuation Anchor
    working_memory_text = ""
    if previous_chapters:
        last_ch = previous_chapters[-1]
        ch_content = str(last_ch.get('content', ''))
        last_words = " ".join(ch_content.split()[-1500:])
        working_memory_text = f"\\n--- KẾT THÚC CỦA CHƯƠNG {last_ch['chapter_number']}: {last_ch['title']} ---\\n{last_words}\\n"
    else:
        working_memory_text = "Đây là chương mở đầu. Hãy viết hoàn toàn mới."'''

match = re.search(r'previous_chapters = \[c for c in all_chapters if c\["chapter_number"\] < next_ch_number.*?working_memory_text \+= f"\\n--- .*?\\n"', content, re.DOTALL)
if match:
    content = content[:match.start()] + new_memory + content[match.end():]
else:
    print('Failed to replace memory logic')

old_prompt_format = r'''prompt = prompts\.WRITING_PROMPT\.format\(
        chapter_number=next_ch_number,
        chapter_title=chapter_record\["title"\],
        title="Truy.*?n 24h Audio",
        blueprint=blueprint_text,
        world_lore=world_lore_text,
        characters=json\.dumps\(chars, ensure_ascii=False, indent=2\),
        history=history_text,
        previous_content=working_memory_text,
        protagonist_name=protagonist_name,
        protagonist_power=protagonist_power,
        protagonist_stats=protagonist_stats,
        failure_flag=str\(failure_flag\)
    \)'''

new_prompt_format = '''prompt = prompts.WRITING_PROMPT.format(
        chapter_number=next_ch_number,
        chapter_title=chapter_record["title"],
        title="Truyen 24h Audio",
        blueprint=blueprint_text,
        world_lore=world_lore_text,
        characters=json.dumps(chars, ensure_ascii=False, indent=2),
        history=history_text,
        previous_content=working_memory_text,
        forbidden_phrases=forbidden_phrases,
        protagonist_name=protagonist_name,
        protagonist_power=protagonist_power,
        protagonist_stats=protagonist_stats,
        failure_flag=str(failure_flag)
    )'''

content = re.sub(old_prompt_format, new_prompt_format, content, flags=re.DOTALL)

prologue_re = r'if next_ch_number == 1:.*?prompt = prompt\.replace\("Constraints:", f"Constraints:\\n\{prologue_instruction\}"\)'
new_prologue = '''if next_ch_number == 1:
        prologue_instruction = (
            f"- CHÚ Ý: ĐÂY LÀ CHƯƠNG MỞ ĐẦU (PROLOGUE). Chỉ dành 1/4 dung lượng để miêu tả bối cảnh. Sau đó BẮT BUỘC phải chuyển cảnh (Time-skip/Location-skip) sang một tình huống có thật, đưa {protagonist_name} vào hành động!\\n"
            f"- KHÔNG liệt kê nhân vật phụ tràn lan. Bắt đầu ngay lập tức.\\n"
        )
        prompt = prompt.replace("INKOS STRUCTURE DIRECTIVES:", f"INKOS STRUCTURE DIRECTIVES:\\n{prologue_instruction}")'''

content = re.sub(prologue_re, new_prologue, content, flags=re.DOTALL)

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated writer.py')
