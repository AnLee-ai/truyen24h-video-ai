import inspect
from gradio_client import Client
import os
import sys

def get_client_kwargs(repo_id: str, hf_token: str):
    """Dynamically determine whether to use token= or hf_token="""
    params = inspect.signature(Client.__init__).parameters
    kwargs = {}
    if "token" in params:
        kwargs["token"] = hf_token
    elif "hf_token" in params:
        kwargs["hf_token"] = hf_token
    return kwargs

def patch_file(filepath, client_str, hf_token_var):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We'll just add a helper function at the top if it's not there.
    helper = '''
def _get_client_kwargs(hf_token):
    import inspect
    from gradio_client import Client
    params = inspect.signature(Client.__init__).parameters
    kwargs = {}
    if "token" in params:
        kwargs["token"] = hf_token
    elif "hf_token" in params:
        kwargs["hf_token"] = hf_token
    return kwargs
'''
    if '_get_client_kwargs' not in content:
        # insert after imports
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import = i
        content = '\n'.join(lines[:last_import+1]) + '\n' + helper + '\n'.join(lines[last_import+1:])
        
    # Replace the client instantiation
    import re
    # Match client = Client("repo", token=...) or hf_token=...
    # Or just replace exactly what we find.
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file('d:/222/src/image_generator.py', 'nothing', 'nothing')
