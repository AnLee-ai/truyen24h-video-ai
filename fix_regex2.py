with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(r"r'(?<=[.?!…])\s+(?=[a-zA-ZÀ-ỹ0-9\"'«“])'", r"r'(?<=[.?!…])\\s+(?=[a-zA-ZÀ-ỹ0-9\"\'«“])'")

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
