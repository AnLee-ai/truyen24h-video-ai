import sys

def fix_css():
    with open('templates/index.css', 'rb') as f:
        content = f.read()
    
    # Try to decode safely
    text = content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
    
    with open('templates/index.css', 'w', encoding='utf-8') as f:
        f.write(text)

fix_css()
