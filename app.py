import gradio as gr
import queue
import threading
import uuid
from src.main import run_chapter_pipeline, app as fastapi_app

def trigger_writing(novel_id):
    import html
    novel_id = html.escape((novel_id or "").strip())
    if not novel_id:
        yield "Vui lòng điền Novel ID!"
        return
        
    try:
        uuid.UUID(novel_id)
    except ValueError:
        yield "Lỗi: Novel ID không đúng định dạng UUID!"
        return
        
    log_queue = queue.Queue()
    
    def log_callback(msg):
        log_queue.put(msg)
        
    try:
        thread = threading.Thread(
            target=run_chapter_pipeline, 
            args=(novel_id,), 
            kwargs={"log_callback": log_callback}
        )
        thread.daemon = True
        thread.start()
    except Exception as e:
        yield f"❌ Không thể khởi tạo tiến trình chạy ngầm: {e}"
        return
        
    accumulated_logs = ["[INFO] Đang khởi động tiến trình..."]
    yield "\n".join(accumulated_logs)
    
    import time
    while thread.is_alive() or not log_queue.empty():
        try:
            msg = log_queue.get(timeout=0.2)
            accumulated_logs.append(msg)
            yield "\n".join(accumulated_logs)
        except queue.Empty:
            time.sleep(0.05)
            continue
            
    # Check if there is an error in logs to show appropriate status
    has_error = any("[ERROR]" in log for log in accumulated_logs)
    if has_error:
        yield "\n".join(accumulated_logs) + "\n\n❌ Tiến trình kết thúc với lỗi."
    else:
        yield "\n".join(accumulated_logs) + "\n\n✅ Hoàn thành! Audio đã được gửi lên Telegram."

# Build Gradio UI
with gr.Blocks(title="Truyện 24h Audio Control Panel") as demo:
    gr.Markdown("# 🎙️ Truyện 24h Audio Control Panel")
    gr.Markdown("🟢 Trạng thái hệ thống: Hoạt động 24/24")
    
    with gr.Row():
        novel_id_input = gr.Textbox(label="Nhập Novel ID (Supabase UUID)", placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000")
        
    run_btn = gr.Button("🚀 Chạy viết chương mới & Tạo Audio", variant="primary")
    output = gr.Textbox(label="Kết quả chạy", interactive=False, lines=15, max_lines=30)
    
    run_btn.click(fn=trigger_writing, inputs=novel_id_input, outputs=output)  # type: ignore[attr-defined]

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 7860))
    print(f"[INFO] Starting server on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port)
