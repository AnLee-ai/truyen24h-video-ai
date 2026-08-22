import sys

def fix_routers():
    with open('src/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from src.api.routers import' not in content:
        insert_code = '''
from src.api.routers import novels, pipelines, settings, tts as tts_router

app.include_router(novels.router, prefix="/api", tags=["Novels"])
app.include_router(pipelines.router, prefix="/api", tags=["Pipelines"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(tts_router.router, prefix="/api", tags=["TTS"])
'''
        content = content.replace('app.mount("/static", StaticFiles(directory="templates"), name="static")', 'app.mount("/static", StaticFiles(directory="templates"), name="static")\n' + insert_code)
        
        with open('src/main.py', 'w', encoding='utf-8') as f:
            f.write(content)

fix_routers()
