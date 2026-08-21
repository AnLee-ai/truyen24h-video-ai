import sys

content = open('app.py', 'r', encoding='utf-8').read()
content = content.replace('int(x.get("chapter_number", 0))', 'int(float(x.get("chapter_number") or 0))')
open('app.py', 'w', encoding='utf-8').write(content)
print('Patched app.py')
