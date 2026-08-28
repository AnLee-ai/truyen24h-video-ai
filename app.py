import uuid
import queue
import threading
import time
import json
import asyncio
from fastapi import Request, Body
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
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

@fastapi_app.get("/api/novels")
def api_get_novels():
    """Lấy danh sách các truyện đang active từ DB."""
    try:
        novels = database.get_active_novels()
        return JSONResponse(content={"status": "success", "data": novels}, media_type="application/json; charset=utf-8")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/history")
def api_get_history(novel_id: str = ""):
    """Lấy lịch sử các video đã sinh."""
    try:
        chapters = database.get_all_chapters(novel_id)
        # Sort by chapter_number desc
        chapters = sorted(chapters, key=lambda x: int(float(x.get("chapter_number") or 0)), reverse=True)
        return JSONResponse(content={"status": "success", "data": chapters[:50]}, media_type="application/json; charset=utf-8")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/settings/get")
def api_get_settings():
    """Đọc cấu hình từ file .env (Masked để bảo mật)"""
    import os
    from dotenv import dotenv_values
    env_path = ".env"
    settings = {}
    if os.path.exists(env_path):
        raw_settings = dotenv_values(env_path)
        for k, v in raw_settings.items():
            if not v:
                settings[k] = ""
            elif k in ["GEMINI_API_KEY", "SUPABASE_KEY", "TELEGRAM_BOT_TOKEN"]:
                settings[k] = f"{v[:4]}...{v[-4:]}" if len(v) > 8 else "***"
            else:
                settings[k] = v
    return {"status": "success", "data": settings}

@fastapi_app.post("/api/settings/update")
async def api_update_settings(request: Request):
    """Cập nhật cấu hình vào file .env an toàn"""
    try:
        payload = await request.json()
        import os
        from dotenv import set_key
        env_path = ".env"
        if not os.path.exists(env_path):
            open(env_path, "w").close()
            
        ALLOWED_KEYS = {
            "GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY", 
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL", "DEFAULT_VOICE"
        }
        
        for k, v in payload.items():
            if k in ALLOWED_KEYS:
                if "..." not in str(v) and "***" not in str(v):
                    set_key(env_path, k, str(v))
                
        return {"status": "success", "message": "Đã cập nhật cấu hình thành công!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.get("/api/tts/preview")
async def api_tts_preview(voice: str = "vi-VN-HoaiMyNeural", text: str = "Xin chào, đây là giọng đọc thử nghiệm."):
    """Tạo audio preview nhanh chóng bằng edge-tts."""
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_file.close()
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(tmp_file.name)
        from starlette.background import BackgroundTask
        return FileResponse(tmp_file.name, media_type="audio/mpeg", background=BackgroundTask(os.remove, tmp_file.name))
    except Exception as e:
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        return {"status": "error", "message": str(e)}

active_pipelines = set()
pipeline_lock = threading.Lock()

@fastapi_app.get("/api/run_pipeline")
async def api_run_pipeline(novel_id: str):
    async def event_generator():
        import html
        n_id = html.escape((novel_id or "").strip())
        if not n_id:
            yield f"data: {json.dumps({'msg': '[ERROR] Vui lòng điền Novel ID!', 'done': True})}\n\n"
            return
            
        try:
            val = uuid.UUID(n_id)
            if str(val) != n_id:
                raise ValueError()
        except ValueError:
            yield f"data: {json.dumps({'msg': '[ERROR] Novel ID không đúng định dạng UUID!', 'done': True})}\n\n"
            return
            
        with pipeline_lock:
            if n_id in active_pipelines:
                yield f"data: {json.dumps({'msg': '[ERROR] Tiến trình cho bộ truyện này đang chạy, vui lòng không spam!', 'done': True})}\n\n"
                return
            active_pipelines.add(n_id)
        try:
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
        finally:
            active_pipelines.discard(n_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@fastapi_app.get("/api/run_thumbnail")
async def api_run_thumbnail(novel_id: str):
    async def event_generator():
        n_id = (novel_id or "").strip()
        if not n_id:
            yield f"data: {json.dumps({'msg': '[ERROR] Vui lòng nhập Novel ID', 'done': True})}\n\n"
            return
            
        yield f"data: {json.dumps({'msg': f'[INFO] Đang lấy thông tin Chapter mới nhất cho Novel: {n_id}...'})}\n\n"
        
        # Giải phóng event loop cho thao tác đọc DB
        chapter = await asyncio.to_thread(database.get_latest_chapter, n_id)
        if not chapter:
            yield f"data: {json.dumps({'msg': '[ERROR] Không tìm thấy Chapter nào. Hãy chạy Viết Chương trước.', 'done': True})}\n\n"
            return
            
        title = chapter.get("title", f"Chương {chapter.get('chapter_number', '?')}")
        video_path = f"output/videos/{chapter.get('id', 'temp')}.mp4"
        job_id = f"thumb_ui_{int(time.time())}"
        
        job_queue.add_job(job_id, run_thumbnail_pipeline, video_path, title)
        
        yield f"data: {json.dumps({'msg': f'[INFO] Bắt đầu 9-Agent Pipeline cho {title}'})}\n\n"
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
