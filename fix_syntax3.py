with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
pattern = r'if next_ch_number == 1:.*?while attempt < max_attempts:'

new_block = r'''if next_ch_number == 1:
        prologue_instruction = (
            f"- CHÚ Ý: ĐÂY LÀ CHƯƠNG MỞ ĐẦU (PROLOGUE). Chỉ dành 1/4 dung lượng để miêu tả bối cảnh. Sau đó BẮT BUỘC phải chuyển cảnh sang một tình huống có thật, đưa {protagonist_name} vào hành động!\n"
            f"- KHÔNG liệt kê nhân vật phụ tràn lan. Bắt đầu ngay lập tức.\n"
        )
        prompt = prompt.replace("INKOS STRUCTURE DIRECTIVES:", f"INKOS STRUCTURE DIRECTIVES:\n{prologue_instruction}")
    
    while attempt < max_attempts:'''

# We must escape backslashes in replacement string for re.sub
content = re.sub(pattern, new_block.replace('\\', '\\\\'), content, flags=re.DOTALL)

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
