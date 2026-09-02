import sys

content = open('src/database.py', 'r', encoding='utf-8').read()
content = content.replace('or ("completed" in audio_url)', '')
open('src/database.py', 'w', encoding='utf-8').write(content)
print('Patched src/database.py')
