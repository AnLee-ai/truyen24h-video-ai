import os, re

# 1. Patch database.py to include GoFile fallback
db_file = r'd:\222\src\database.py'
with open(db_file, 'r', encoding='utf-8') as f:
    db_content = f.read()

gofile_func = '''
def upload_to_gofile_fallback(file_path: str) -> str:
    import requests
    print(f"[INFO] Chuyển hướng upload {os.path.basename(file_path)} sang GoFile (Bypass 50MB limit)...")
    try:
        servers_res = requests.get('https://api.gofile.io/servers', timeout=15).json()
        if servers_res.get('status') == 'ok':
            server = servers_res['data']['servers'][0]['name']
            url = f'https://{server}.gofile.io/contents/uploadfile'
            with open(file_path, 'rb') as f_obj:
                res = requests.post(url, files={'file': (os.path.basename(file_path), f_obj)}, timeout=600).json()
                if res.get('status') == 'ok':
                    dlink = res['data']['downloadPage']
                    print(f"[SUCCESS] Upload GoFile thành công! Link: {dlink}")
                    return dlink
    except Exception as e:
        print(f"[ERROR] GoFile fallback failed: {e}")
    return ""

def upload_file_to_supabase(
'''

db_content = db_content.replace('def upload_file_to_supabase(', gofile_func.strip() + '\n')

# Inside upload_file_to_supabase, if all retries fail, call gofile
replace_gofile_fallback = '''
            if attempt == max_retries - 1:
                print(f"[ERROR] Thất bại khi upload {file_path} lên Supabase Storage: {e}")
                # KÍCH HOẠT FALLBACK GOFILE KHI SUPABASE THẤT BẠI
                gofile_link = upload_to_gofile_fallback(file_path)
                return gofile_link
'''

db_content = re.sub(
    r"if attempt == max_retries - 1:\s*print\(f\"\[ERROR\] Thất bại khi upload {file_path}.*?\n\s*return \"\"",
    replace_gofile_fallback.strip(),
    db_content,
    flags=re.DOTALL
)

with open(db_file, 'w', encoding='utf-8') as f: f.write(db_content)


# 2. Fix storage_cleaner.py
cleaner_file = r'd:\222\src\storage_cleaner.py'
with open(cleaner_file, 'r', encoding='utf-8') as f:
    cl_content = f.read()

cl_content = cl_content.replace('scenes_dir = os.path.join(target_dir, "scenes")', 'scenes_dir = os.path.join(target_dir, "images")')

with open(cleaner_file, 'w', encoding='utf-8') as f: f.write(cl_content)

print("Patched database.py and storage_cleaner.py")
