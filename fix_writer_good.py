import subprocess
import os
import re

# Get pure bytes from the last GOOD commit
git_exe = r'C:\Users\david\AppData\Local\GitHubDesktop\app-3.6.3\resources\app\git\cmd\git.exe'
pure_bytes = subprocess.check_output([git_exe, 'show', '0d47f14:src/writer.py'])
content = pure_bytes.decode('utf-8')

# Apply modifications
content = content.replace('gemini-2.0-flash-lite', 'gemini-3.5-flash-lite')
content = content.replace('gemini-2.0-flash', 'gemini-3.6-flash')
content = re.sub(r'(?s)# =========================================================================\n\s*# ĐƯỜNG CƠ DỰ PHÒNG 2: Local Mangstoon_AI Engine.*?# =========================================================================\n\s*local_mangstoon = call_mangstoon_ai\(prompt\)\n\s*if local_mangstoon and len\(local_mangstoon.strip\(\).split\(\)\) > 10:\n\s*print\("\[SUCCESS\] Local Mangstoon_AI succeeded!"\)\n\s*return local_mangstoon.strip\(\)\n', '', content)
content = "import os\nfrom gradio_client import Client\n" + content

inkos_func = '''
def call_inkos_cloud(prompt: str) -> str:
    print("[INFO] Gửi yêu cầu sáng tác tới Inkos (Hugging Face Cloud)...")
    try:
        hf_token = os.environ.get("HF_TOKEN")
        client = Client("AnLee-ai/truyen24h-video-ai", token=hf_token)
        result = client.predict(
            prompt=prompt,
            api_name="/generate_story"
        )
        if "Lỗi" in result:
            print(f"[WARNING] Inkos trả về lỗi: {result}")
            return ""
        return str(result)
    except Exception as e:
        print(f"[ERROR] Lỗi gọi Inkos Cloud: {e}")
        return ""
'''
content = content.replace('@cached(ttl_seconds=86400)\ndef call_gemini', inkos_func + '\n@cached(ttl_seconds=86400)\ndef call_gemini')
content = content.replace('final_content = call_gemini(current_prompt)', 
    'final_content = call_inkos_cloud(current_prompt)\n            if not final_content or len(final_content.strip()) < 10:\n                final_content = call_gemini(current_prompt)')

with open(r'd:\222\src\writer.py', 'w', encoding='utf-8') as f:
    f.write(content)
