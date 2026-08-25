import re

try:
    content = open(r'd:\222\src\writer.py', 'r', encoding='utf-8').read()
except UnicodeDecodeError:
    content = open(r'd:\222\src\writer.py', 'r', encoding='cp1252').read()

def try_decode(match):
    s = match.group(0)
    try:
        # Try to fix the double encoding
        return s.encode('cp1252').decode('utf-8')
    except:
        return s

# This regex matches blocks of corrupted characters
content = re.sub(r'[ÃÂÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+', try_decode, content)

open(r'd:\222\src\writer.py', 'w', encoding='utf-8').write(content)
print("done")
