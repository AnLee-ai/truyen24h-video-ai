import re

main_file = r'd:\222\src\main.py'
with open(main_file, 'r', encoding='utf-8') as f:
    m_content = f.read()

# Remove the fake URL forcing logic
m_content = re.sub(
    r"# ?m bo video_public_url luA'n chca link CDN trc tip 100%.*?_16_9\.mp4\"", 
    "", 
    m_content, 
    flags=re.DOTALL
)

with open(main_file, 'w', encoding='utf-8') as f: f.write(m_content)

uploader_file = r'd:\222\src\telegram_uploader.py'
with open(uploader_file, 'r', encoding='utf-8') as f:
    u_content = f.read()

u_content = re.sub(
    r"if not final_cdn_url and config\.SUPABASE_URL and video_path:.*?final_cdn_url = f.*?\{filename_rel\}\"", 
    "", 
    u_content, 
    flags=re.DOTALL
)

with open(uploader_file, 'w', encoding='utf-8') as f: f.write(u_content)
print('Fixed fake URLs')
