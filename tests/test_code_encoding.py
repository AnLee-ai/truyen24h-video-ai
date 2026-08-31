import os
import re

def test_no_mojibake_in_source_code():
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    # Match double or triple encoded UTF-8 bytes like Ãƒ, Ã¡, etc.
    mojibake_re = re.compile(r'[\xc3\xc4\xc5][\x80-\xbf]')
    
    violating_files = []
    
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            
            fpath = os.path.join(root, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            matches = mojibake_re.findall(content)
            if matches:
                violating_files.append((fname, len(matches)))
                
    assert not violating_files, f"Mojibake found in files: {violating_files}"
