with open('d:/222/src/writer.py', 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')
    
# Find the function definition
start = -1
for i, l in enumerate(lines):
    if l.startswith('def call_inkos_cloud(prompt: str) -> str:'):
        start = i
        break

if start != -1:
    # Find the end of the function (before the next def or decorator)
    end = start + 1
    while end < len(lines):
        if lines[end].startswith('def ') or lines[end].startswith('@'):
            break
        end += 1
        
    # Replace the block
    new_lines = lines[:start] + ['def call_inkos_cloud(prompt: str) -> str:', '    return ""', ''] + lines[end:]
    
    with open('d:/222/src/writer.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("Fixed!")
else:
    print("Not found")
