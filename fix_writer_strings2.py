with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('f"Ch\\xc6\\xb0\\xc6\\xa1ng {next_ch_number}"', 'f"Chương {next_ch_number}"')
content = content.replace('f"BLUEPRINT: Di\\xe1\\xbb\\x85n bi\\xe1\\xba\\xbfn ti\\xe1\\xba\\xbfp theo."', 'f"BLUEPRINT: Diễn biến tiếp theo."')

with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed writer.py create_chapter strings')
