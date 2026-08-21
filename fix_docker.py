import sys

def fix_dockerfile():
    with open('Dockerfile', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'ENV PYTHONPATH=/app' not in content:
        content = content.replace('WORKDIR /app', 'WORKDIR /app\n\n# Fix module path\nENV PYTHONPATH=/app')
        
    with open('Dockerfile', 'w', encoding='utf-8') as f:
        f.write(content)

fix_dockerfile()
