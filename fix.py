import sys

def fix_file():
    with open('src/writer.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if 'e        "title": "Default Arc"' in line:
            print(f"Found error at line {i+1}")
            lines[i] = '        "title": "Default Arc",\n'
            
        if '0e 0' in line:
            print(f"Found error 2 at line {i+1}")
            lines[i] = line.replace('0e 0', '0')
            
        if 'rs if str(c.get("chapter_number"' in line:
            print(f"Found duplicate trash at line {i+1}")
            lines[i] = ""
            # remove next few lines of duplicates
            for j in range(1, 23):
                if i+j < len(lines):
                    lines[i+j] = ""

    with open('src/writer.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
fix_file()
