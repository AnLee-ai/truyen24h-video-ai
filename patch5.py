import sys

content = open('src/writer.py', 'r', encoding='utf-8').read()

# Fix import json at line 588 and 877
content = content.replace('import os, json', 'import os')

# Fix encoding issue at line 882
bad_text = '(TÃƒÂ¡Ã‚ÂºÃ‚Â­p'
good_text = '(Tập'
if bad_text in content:
    content = content.replace(bad_text, good_text)
elif '(TÃ¡ÂºÂ­p' in content:
    content = content.replace('(TÃ¡ÂºÂ­p', '(Tập')
else:
    # Use regex to fix it if it's slightly different
    import re
    content = re.sub(r'\(T[^a-zA-Z0-9\s]+p', '(Tập', content)

open('src/writer.py', 'w', encoding='utf-8').write(content)
print('Patched src/writer.py')
