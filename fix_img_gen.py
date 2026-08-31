import re

with open('d:/222/src/image_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """
    import inspect
    kwargs = {}
    params = inspect.signature(Client.__init__).parameters
    if "token" in params:
        kwargs["token"] = os.environ.get("HF_TOKEN")
    elif "hf_token" in params:
        kwargs["hf_token"] = os.environ.get("HF_TOKEN")
    client = Client("AnLee-ai/my-story-diffusion", **kwargs)
"""

content = re.sub(
    r'client = Client\("AnLee-ai/my-story-diffusion", token=os.environ.get\("HF_TOKEN"\)\)',
    replacement.strip(),
    content
)

with open('d:/222/src/image_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed image_generator.py')
