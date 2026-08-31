with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'sentences = re.split' in line:
        # Just use a safe ascii regex for splitting sentences safely
        lines[i] = "        sentences = re.split(r'(?<=[.?!])\\\\s+(?=[A-Za-z0-9])', para)\n"
        print('Fixed regex at line', i+1)

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
