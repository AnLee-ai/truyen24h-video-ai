import re

with open('d:/222/src/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update audit_chapter_quality
content = content.replace("word_count < 1000", "word_count < 2000")
content = content.replace("1,000", "2,000")
content = content.replace("< 1000", "< 2000")

# Use regex to replace the guardrail
pattern = r'if not is_resuming_video and \(not chapter_content or len\(chapter_content\.split\(\)\) < 2500\):.*?return'
new_guardrail = '''if not chapter_content or len(chapter_content.split()) < 2000:
            print(f"[WARNING] Nội dung chương chưa đạt tiêu chuẩn BẮT BUỘC (>2000 từ). Độ dài thực tế: {len(chapter_content.split()) if chapter_content else 0} từ. Tự động dừng tiến trình an toàn để AI viết lại.")
            return'''

content = re.sub(pattern, new_guardrail, content, flags=re.DOTALL)

with open('d:/222/src/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated main.py')
