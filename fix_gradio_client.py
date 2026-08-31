import inspect
import re

with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """        import inspect
        from gradio_client import Client
        params = inspect.signature(Client.__init__).parameters
        kwargs = {}
        if "token" in params:
            kwargs["token"] = hf_token
        elif "hf_token" in params:
            kwargs["hf_token"] = hf_token
            
        client = Client("AnLee-ai/truyen24h-video-ai", **kwargs)"""

# We need to replace the try/except block.
# Let's use regex to find it.
pattern = r"        try:\n            client = Client\(\"AnLee-ai/truyen24h-video-ai\", token=hf_token\)\n        except TypeError:\n            client = Client\(\"AnLee-ai/truyen24h-video-ai\", hf_token=hf_token\)"

if re.search(pattern, content):
    content = re.sub(pattern, replacement, content)
    with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully replaced try/except block.")
else:
    print("Could not find the try/except block.")
