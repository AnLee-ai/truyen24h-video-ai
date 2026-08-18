import sys
import json

with open('app.py', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
'''@fastapi_app.get("/api/run_pipeline")
async def api_run_pipeline(novel_id: str):''',
'''from fastapi import Request

@fastapi_app.get("/api/cancel_pipeline")
async def api_cancel_pipeline(novel_id: str):
    n_id = (novel_id or "").strip()
    with pipeline_lock:
        if n_id in active_pipelines:
            active_pipelines.discard(n_id)
            return {"status": "success", "message": "Đã hủy theo dõi tiến trình (Thread ngầm có thể vẫn chạy một lúc)."}
    return {"status": "error", "message": "Không tìm thấy tiến trình đang chạy."}

@fastapi_app.get("/api/run_pipeline")
async def api_run_pipeline(novel_id: str, request: Request):'''
)

content = content.replace(
'''            while thread.is_alive() or not log_queue.empty():
                try:
                    msg = log_queue.get_nowait()
                    if "[ERROR]" in msg:
                        has_error = True
                    yield f"data: {json.dumps({'msg': msg})}\\n\\n"
                except queue.Empty:
                    await asyncio.sleep(0.1)''',
'''            while thread.is_alive() or not log_queue.empty():
                if await request.is_disconnected():
                    active_pipelines.discard(n_id)
                    break
                if n_id not in active_pipelines:
                    yield f"data: {json.dumps({'msg': '[WARN] Tiến trình đã bị hủy bởi người dùng.', 'done': True})}\\n\\n"
                    break
                try:
                    msg = log_queue.get(timeout=0.1)
                    if "[ERROR]" in msg:
                        has_error = True
                    yield f"data: {json.dumps({'msg': msg})}\\n\\n"
                except queue.Empty:
                    pass'''
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
