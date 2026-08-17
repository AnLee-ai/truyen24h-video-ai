import os, glob

for f in glob.glob('mangstoon_ai/**/*.py', recursive=True):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'GOOGLE_API_KEY' in content:
        content = content.replace('os.environ["GOOGLE_API_KEY"]', 'os.getenv("GOOGLE_API_KEY", "DUMMY_KEY_FOR_TESTS")')
        content = content.replace("os.environ['GOOGLE_API_KEY']", 'os.getenv("GOOGLE_API_KEY", "DUMMY_KEY_FOR_TESTS")')
        content = content.replace('os.getenv("GOOGLE_API_KEY", "")', 'os.getenv("GOOGLE_API_KEY", "DUMMY_KEY_FOR_TESTS")')
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Fixed {f}")
