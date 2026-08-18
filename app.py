import uuid
import queue
import threading
import time
import json
import asyncio
from fastapi import Request, Body
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
import tempfile
import edge_tts
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.main import run_chapter_pipeline, app as fastapi_app
from src import database
from src.queue_manager import job_queue
from src.thumbnail_agent.pipeline import run_thumbnail_pipeline

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
fastapi_app.mount("/static", StaticFiles(directory="templates"), name="static")

@fastapi_app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

def fix_encoding(text):
    if not isinstance(text, str): return text
    
    # Thử decode từ cp1252 (chuẩn Windows hay gây lỗi mojibake nhất)
    try:
        t1 = text.encode('cp1252').decode('utf-8')
        try:
            # Nếu bị double-encoding
            t2 = t1.encode('cp1252').decode('utf-8')
            return t2
        except:
            return t1
    except:
        pass
        
    # Thử fallback sang latin-1
    try:
        t1 = text.encode('latin-1').decode('utf-8')
        try:
            t2 = t1.encode('latin-1').decode('utf-8')
            return t2
        except:
            return t1
    except:
        pass

    return text

@fastapi_app.get("/api/run_pipeline")
async def api_run_pipeline(novel_id: str):
    async def event_generator():
        import html
        n_id = html.escape((novel_id or "").strip())
        if not n_id:
            yield f"data: {json.dumps({'msg': '[ERROR] Vui lòng điền Novel ID!', 'done': True})}\n\n"
            return
            
        try:
            uuid.UUID(n_id)
        except ValueError:
            yield f"data: {json.dumps({'msg': '[ERROR] Novel ID không đúng định dạng UUID!', 'done': True})}\n\n"
            return
            
        log_queue = queue.Queue()
        def log_callback(msg):
            log_queue.put(msg)
            
        try:
            thread = threading.Thread(
                target=run_chapter_pipeline, 
                args=(n_id,), 
                kwargs={"log_callback": log_callback}
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            yield f"data: {json.dumps({'msg': f'[ERROR] Không thể khởi tạo tiến trình: {e}', 'done': True})}\n\n"
            return
            
        yield f"data: {json.dumps({'msg': '[INFO] Đang khởi động tiến trình...'})}\n\n"
        
        has_error = False
        while thread.is_alive() or not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                if "[ERROR]" in msg:
                    has_error = True
                yield f"data: {json.dumps({'msg': msg})}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.1)
                
        if has_error:
            yield f"data: {json.dumps({'msg': '[ERROR] Tiến trình kết thúc với lỗi.', 'done': True})}\n\n"
        else:
            yield f"data: {json.dumps({'msg': '✅ Hoàn thành! Audio đã được gửi lên Telegram.', 'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")



if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 7860))
    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("app:fastapi_app", host="0.0.0.0", port=port)
