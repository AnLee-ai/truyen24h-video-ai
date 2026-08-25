import re

text = open(r'd:\222\src\writer.py', 'r', encoding='utf-8').read()
matches = re.finditer(r'[\"\'].*?[ÃÂÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+.*?[\"\']', text)
for m in matches:
    print(repr(m.group(0)))
