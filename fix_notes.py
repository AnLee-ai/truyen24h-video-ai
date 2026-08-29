import re
with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_inkos = """def call_inkos_cloud(prompt: str) -> str:
    print("[INFO] Gửi yêu cầu sáng tác tới Inkos (Hugging Face Cloud)...")
    try:
        import requests
        import os
        hf_token = os.environ.get("HF_TOKEN")
        url = "https://anlee-ai-truyen24h-video-ai.hf.space/gradio_api/call/predict"
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        
        # We use /predict because the API info showed it. But wait, I should check the exact endpoint first.
        # Wait, if gradio_api/call/predict doesn't work, maybe /gradio_api/run/predict? Or just fallback to Gemini.
        return ""
    except Exception as e:
        print(f"[ERROR] Lỗi gọi Inkos Cloud: {e}")
        return ""
"""

# Actually, wait, let me just add sys.stdout.reconfigure to main.py instead!
