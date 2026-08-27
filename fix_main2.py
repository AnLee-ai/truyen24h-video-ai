import re
main_file = r'd:\222\src\main.py'
with open(main_file, 'r', encoding='utf-8') as f:
    m_content = f.read()

m_content = re.sub(
    r"#.*?video_public_url.*?\n\s*if not video_public_url and config\.SUPABASE_URL:\n\s*video_public_url =.*?16_9\.mp4\"",
    "",
    m_content,
    flags=re.DOTALL
)

with open(main_file, 'w', encoding='utf-8') as f: f.write(m_content)
print('Fixed main again')
