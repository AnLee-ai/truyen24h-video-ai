import sys

with open('d:/222/src/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'sys.stdout.reconfigure(encoding="utf-8")' not in content:
    content = 'import sys\ntry:\n    sys.stdout.reconfigure(encoding="utf-8")\nexcept:\n    pass\n' + content
    with open('d:/222/src/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
with open('d:/222/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'sys.stdout.reconfigure(encoding="utf-8")' not in content:
    content = 'import sys\ntry:\n    sys.stdout.reconfigure(encoding="utf-8")\nexcept:\n    pass\n' + content
    with open('d:/222/app.py', 'w', encoding='utf-8') as f:
        f.write(content)

print('Enforced UTF-8 stdout.')
