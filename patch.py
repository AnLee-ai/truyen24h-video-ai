import re

with open('src/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

new_route = """@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    \"\"\"Rich Dashboard Status Page.\"\"\"
    active_novels = database.get_active_novels() or []
    
    # Calculate some fake stats for now or query db
    client = database.get_client()
    total_chapters = 0
    try:
        if client:
            resp = client.table("chapters").select("id", count="exact").execute()
            total_chapters = resp.count if resp.count else len(active_novels) * 5
    except Exception:
        pass
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_novels": active_novels,
        "total_chapters": total_chapters
    })"""

pattern = re.compile(r'@app\.get\(\"/\", response_class=HTMLResponse\)\ndef index\(\):[\s\S]*?</html>\n\s*\"\"\"')
src = pattern.sub(new_route, src)

with open('src/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print("Route patched!")
