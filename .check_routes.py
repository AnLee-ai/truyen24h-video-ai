import re, sys
sys.stdout.reconfigure(encoding='utf-8')

router_files = [
    'src/api/routers/novels.py',
    'src/api/routers/settings.py',
    'src/api/routers/pipelines.py',
    'src/api/routers/tts.py',
    'app.py',
]

backend_routes = set()
for f in router_files:
    content = open(f, encoding='utf-8').read()
    prefix = '/api' if 'routers' in f else ''
    for m in re.finditer(r'@(?:router|fastapi_app)\.(get|post|put|delete|patch)\("([^"]+)"', content):
        backend_routes.add(prefix + m.group(2))

print("=== BACKEND ROUTES ===")
for r in sorted(backend_routes):
    print(r)

# Extract fetch calls from app.js
js_content = open('templates/app.js', encoding='utf-8').read()
print("\n=== FRONTEND FETCH CALLS ===")
missing = []
for m in re.finditer(r"fetch\(`(/api/[^`?'\"]+)", js_content):
    url = m.group(1)
    # Normalize dynamic params like ${...}
    normalized = re.sub(r'\$\{[^}]+\}', '{param}', url)
    print(f"  {url}")

for m in re.finditer(r"fetch\('(/api/[^']+)'", js_content):
    url = m.group(1)
    print(f"  {url}")
    if url not in backend_routes:
        missing.append(url)

for m in re.finditer(r'fetch\("(/api/[^"]+)"', js_content):
    url = m.group(1)
    print(f"  {url}")
    if url not in backend_routes:
        missing.append(url)

print("\n=== MISSING ROUTES (404 candidates) ===")
if missing:
    for r in missing:
        print(f"  MISSING: {r}")
else:
    print("  (none - all static fetch URLs found in backend)")
