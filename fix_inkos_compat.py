import re

with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def call_inkos_cloud(prompt: str) -> str:
    print("[INFO] G\u00e1\u00bb\u00adi y\u00c3\u00aau c\u00e1\u00ba\u00a7u s\u00c3\u00a1ng t\u00c3\u00a1c t\u00e1\u00bb\u009bi Inkos (Hugging Face Cloud)...")
    try:
        hf_token = os.environ.get("HF_TOKEN")
        client = Client("AnLee-ai/truyen24h-video-ai", token=hf_token)
        result = client.predict(
            prompt=prompt,
            api_name="/generate_story"
        )
        if "L\u00e1\u00bb\u0097i" in result:
            print(f"[WARNING] Inkos tr\u00e1\u00ba\u00a3 v\u00e1\u00bb\u0081 l\u00e1\u00bb\u0097i: {result}")
            return ""
        return str(result)
    except Exception as e:
        print(f"[ERROR] L\u00e1\u00bb\u0097i g\u00e1\u00bb\u008di Inkos Cloud: {e}")
        return ""'''

new = '''def call_inkos_cloud(prompt: str) -> str:
    print("[INFO] G\u1eedi y\u00eau c\u1ea7u s\u00e1ng t\u00e1c t\u1edbi Inkos (Hugging Face Cloud)...")
    try:
        hf_token = os.environ.get("HF_TOKEN")
        # T\u01b0\u01a1ng th\u00edch c\u1ea3 gradio_client c\u0169 (hf_token=) v\u00e0 m\u1edbi (token=)
        try:
            client = Client("AnLee-ai/truyen24h-video-ai", token=hf_token)
        except TypeError:
            client = Client("AnLee-ai/truyen24h-video-ai", hf_token=hf_token)
        result = client.predict(
            prompt=prompt,
            api_name="/generate_story"
        )
        if "L\u1ed7i" in result:
            print(f"[WARNING] Inkos tr\u1ea3 v\u1ec1 l\u1ed7i: {result}")
            return ""
        return str(result)
    except Exception as e:
        print(f"[ERROR] L\u1ed7i g\u1ecdi Inkos Cloud: {e}")
        return ""'''

if old in content:
    content = content.replace(old, new)
    with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK: Replaced call_inkos_cloud with compat version")
else:
    print("WARN: old pattern not found, trying line-based approach")
    # Just replace the specific line
    content = content.replace(
        'client = Client("AnLee-ai/truyen24h-video-ai", token=hf_token)',
        '''# Tương thích cả gradio_client cũ (hf_token=) và mới (token=)
        try:
            client = Client("AnLee-ai/truyen24h-video-ai", token=hf_token)
        except TypeError:
            client = Client("AnLee-ai/truyen24h-video-ai", hf_token=hf_token)'''
    )
    with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK: Line-based replacement done")
