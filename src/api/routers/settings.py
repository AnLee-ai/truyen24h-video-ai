from fastapi import APIRouter, Request
from pydantic import BaseModel
import os
from dotenv import dotenv_values, set_key

router = APIRouter()

class SettingsUpdate(BaseModel):
    GEMINI_API_KEY: str = None
    GROQ_API_KEY: str = None
    SUPABASE_URL: str = None
    SUPABASE_KEY: str = None
    TELEGRAM_BOT_TOKEN: str = None
    TELEGRAM_CHAT_ID: str = None
    DISCORD_WEBHOOK_URL: str = None
    DEFAULT_VOICE: str = None
    DEFAULT_RATE: str = None
    DEFAULT_PITCH: str = None
    DEFAULT_RATE: str = None
    DEFAULT_PITCH: str = None
    DEFAULT_RATE: str = None
    DEFAULT_PITCH: str = None

@router.get("/settings")
def api_get_settings():
    """Đọc cấu hình từ file .env (Masked để bảo mật)"""
    env_path = ".env"
    settings = {}
    if os.path.exists(env_path):
        raw_settings = dotenv_values(env_path)
        for k, v in raw_settings.items():
            if not v:
                settings[k] = ""
            elif k in ["GEMINI_API_KEY", "SUPABASE_KEY", "TELEGRAM_BOT_TOKEN"]:
                settings[k] = f"{v[:4]}...{v[-4:]}" if v and len(v) > 8 else "***"
            else:
                settings[k] = v
    return {"status": "success", "data": settings}

@router.post("/settings/update")
async def api_update_settings(payload: SettingsUpdate):
    """Cập nhật cấu hình vào file .env an toàn với Pydantic Validation"""
    try:
        env_path = ".env"
        if not os.path.exists(env_path):
            open(env_path, "w").close()
            
        data = payload.dict(exclude_unset=True, exclude_none=True)
        for k, v in data.items():
            if "..." not in str(v) and "***" not in str(v):
                set_key(env_path, k, str(v))
                
        return {"status": "success", "message": "Đã cập nhật cấu hình thành công!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
