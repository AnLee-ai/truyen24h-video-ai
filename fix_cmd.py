import sys

def fix_cmd():
    with open('Dockerfile', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('CMD ["python", "src/main.py", "--action", "serve"]', 'CMD ["python", "-m", "src.main", "--action", "serve"]')
        
    with open('Dockerfile', 'w', encoding='utf-8') as f:
        f.write(content)

fix_cmd()
