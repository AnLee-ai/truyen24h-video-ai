import uuid
import queue
import threading
import time
import json
import asyncio
from fastapi import Request, Body
from pydantic import BaseModel
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
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@fastapi_app.get("/api/novels")
def api_get_novels():
    """Lấy danh sách các truyện đang active từ DB."""
    try:
        novels = database.get_active_novels()
        return {"status": "success", "data": novels}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/history")
def api_get_history(novel_id: str = ""):
    """Lấy lịch sử các video đã sinh."""
    try:
        chapters = database.get_all_chapters(novel_id)
        # Sort by chapter_number desc
        chapters = sorted(chapters, key=lambda x: int(x.get("chapter_number", 0)), reverse=True)
        return {"status": "success", "data": chapters[:50]} # Trả về 50 chap mới nhất
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/settings/get")
def api_get_settings():
    """Đọc cấu hình từ file .env"""
    import os
    env_path = ".env"
    settings = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    settings[k.strip()] = v.strip()
    return {"status": "success", "data": settings}

@fastapi_app.post("/api/settings/update")
async def api_update_settings(request: Request):
    """Cập nhật cấu hình vào file .env"""
    try:
        payload = await request.json()
        import os
        env_path = ".env"
        
        # Read existing
        lines = []
        updated_keys = set()
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
        # Update lines
        new_lines = []
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                k, _ = line.split("=", 1)
                k = k.strip()
                if k in payload:
                    new_lines.append(f"{k}={payload[k]}\n")
                    updated_keys.add(k)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
                
        # Append new keys
        for k, v in payload.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}\n")
                
        # Write back
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        return {"status": "success", "message": "Đã cập nhật cấu hình thành công!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
