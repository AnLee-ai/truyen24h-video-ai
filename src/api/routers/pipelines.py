from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import uuid
import json
import asyncio
import html
import time
import queue
import threading
from pydantic import BaseModel

from src.main import run_chapter_pipeline
from src import database
from src.queue_manager import job_queue
from src.thumbnail_agent.pipeline import run_thumbnail_pipeline

router = APIRouter()

active_pipelines = set()
pipeline_lock = threading.Lock()

class NovelRequest(BaseModel):
    novel_id: str

@router.get("/cancel_pipeline")
async def api_cancel_pipeline(novel_id: str):
    n_id = (novel_id or "").strip()
    with pipeline_lock:
        if n_id in active_pipelines:
            active_pipelines.discard(n_id)
            return {"status": "success", "message": "Đã hủy theo dõi tiến trình (Thread ngầm có thể vẫn chạy một lúc)."}
    return {"status": "error", "message": "Không tìm thấy tiến trình đang chạy."}

@router.get("/run_pipeline")
async def api_run_pipeline(novel_id: str, request: Request):
    async def event_generator():
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
                if await request.is_disconnected():
                    active_pipelines.discard(n_id)
                    break
                if n_id not in active_pipelines:
                    yield f"data: {json.dumps({'msg': '[WARN] Tiến trình đã bị hủy bởi người dùng.', 'done': True})}\n\n"
                    break
                try:
                    msg = log_queue.get(timeout=0.1)
                    if "[ERROR]" in msg:
                        has_error = True
                    yield f"data: {json.dumps({'msg': msg})}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.1) # Yield control
                    
            if has_error:
                yield f"data: {json.dumps({'msg': '[ERROR] Tiến trình kết thúc với lỗi.', 'done': True})}\n\n"
            else:
                yield f"data: {json.dumps({'msg': '✅ Hoàn thành! Audio đã được gửi lên Telegram.', 'done': True})}\n\n"
        finally:
            active_pipelines.discard(n_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/run_thumbnail")
async def api_run_thumbnail(novel_id: str):
    async def event_generator():
        n_id = (novel_id or "").strip()
        if not n_id:
            yield f"data: {json.dumps({'msg': '[ERROR] Vui lòng nhập Novel ID', 'done': True})}\n\n"
            return
            
        yield f"data: {json.dumps({'msg': f'[INFO] Đang lấy thông tin Chapter mới nhất cho Novel: {n_id}...'})}\n\n"
        
        # Async DB call
        chapter = await asyncio.to_thread(database.get_latest_chapter, n_id)
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
