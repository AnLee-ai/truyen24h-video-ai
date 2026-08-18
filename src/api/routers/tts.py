from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import tempfile
import os
import edge_tts

router = APIRouter()

@router.get("/tts/preview")
async def api_tts_preview(voice: str = "vi-VN-HoaiMyNeural", text: str = "Xin chào, đây là giọng đọc thử nghiệm."):
    """Tạo audio preview nhanh chóng bằng edge-tts."""
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_file.close()
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(tmp_file.name)
        return FileResponse(tmp_file.name, media_type="audio/mpeg", background=BackgroundTask(os.remove, tmp_file.name))
    except Exception as e:
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        return {"status": "error", "message": str(e)}
