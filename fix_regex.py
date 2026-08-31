with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "sentences = re.split(" in line and "a-zA-Z" in line:
        new_lines.append("        sentences = re.split(r'(?<=[.?!…])\s+(?=[a-zA-ZÀ-ỹ0-9\"\'«“])', para)\n")
    else:
        new_lines.append(line)

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Fixed regex in writer.py")
