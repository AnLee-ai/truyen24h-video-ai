import uuid
import queue
import threading
import time
import json
import asyncio
from fastapi import Request
from fastapi.responses import HTMLResponse, StreamingResponse
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
    return templates.TemplateResponse("index.html", {"request": request})

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

@fastapi_app.get("/api/run_thumbnail")
async def api_run_thumbnail(novel_id: str):
    async def event_generator():
        n_id = (novel_id or "").strip()
        if not n_id:
            yield f"data: {json.dumps({'msg': '[ERROR] Vui lòng nhập Novel ID', 'done': True})}\n\n"
            return
            
        yield f"data: {json.dumps({'msg': f'[INFO] Đang lấy thông tin Chapter mới nhất cho Novel: {n_id}...'})}\n\n"
        
        # Blocking call but should be fast
        chapter = database.get_latest_chapter(n_id)
        if not chapter:
            yield f"data: {json.dumps({'msg': '[ERROR] Không tìm thấy Chapter nào. Hãy chạy Viết Chương trước.', 'done': True})}\n\n"
            return
            
        title = chapter.get("title", f"Chương {chapter.get('chapter_number', '?')}")
        video_path = f"output/videos/{chapter.get('id', 'temp')}.mp4"
        job_id = f"thumb_ui_{int(time.time())}"
        
        job_queue.add_job(job_id, run_thumbnail_pipeline, video_path, title)
        
        yield f"data: {json.dumps({'msg': f'[INFO] Bắt đầu 9-Agent Pipeline cho \'{title}\''})}\n\n"
        yield f"data: {json.dumps({'msg': f'[INFO] Video Path: {video_path}'})}\n\n"
        yield f"data: {json.dumps({'msg': f'[INFO] Job ID: {job_id}'})}\n\n"
        yield f"data: {json.dumps({'msg': '[INFO] Đang chạy nền... Vui lòng chờ...'})}\n\n"
        
        while True:
            status = job_queue.get_job_status(job_id)
            if status["status"] == "completed":
                yield f"data: {json.dumps({'msg': '[SUCCESS] Hoàn thành! Kiểm tra logs trên terminal.', 'done': True})}\n\n"
                break
            elif status["status"] == "failed":
                err = status.get('error', 'Unknown')
                yield f"data: {json.dumps({'msg': f'[ERROR] Lỗi: {err}', 'done': True})}\n\n"
                break
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 7860))
    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("app:fastapi_app", host="0.0.0.0", port=port)
