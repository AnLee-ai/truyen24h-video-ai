with open('d:/222/src/image_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('hf_token=os.environ.get("HF_TOKEN")', 'token=os.environ.get("HF_TOKEN")')
with open('d:/222/src/image_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content2 = f.read()
content2 = content2.replace('hf_token=hf_token', 'token=hf_token')
with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.write(content2)
