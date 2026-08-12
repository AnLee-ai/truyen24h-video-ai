import os
import sys
import shutil
import urllib.request
import requests
from src import config, database, key_rotator

def run_health_check():
    """Kiểm tra toàn bộ hệ thống (Health Check) trước khi chạy workflow."""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    print("=" * 60)
    print("🏥 HEALTH CHECK & DIAGNOSTICS - TRUYỆN 24H AI STUDIO")
    print("=" * 60)
    
    checks = []
    
    # 1. FFmpeg
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    checks.append(("FFmpeg Binary", "OK" if ffmpeg_ok else "MISSING"))
    
    # 2. Supabase DB Connection
    db_ok = False
    try:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            client = database.get_client()
            res = client.table("novels").select("id").limit(1).execute()
            db_ok = True
    except Exception as e:
        print(f"[WARNING] Supabase Check Error: {e}")
    checks.append(("Supabase Database", "CONNECTED" if db_ok else "DISCONNECTED"))
    
    # 3. Gemini API Key
    gemini_key = key_rotator.get_gemini_key() or config.GEMINI_API_KEY
    checks.append(("Gemini API Key", f"CONFIGURED ({gemini_key[:6]}...)" if gemini_key else "MISSING"))
    
    # 4. Telegram Bot API
    tg_ok = False
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
            r = requests.get(url, timeout=10)
            tg_ok = r.status_code == 200
        except Exception:
            pass
    checks.append(("Telegram Bot API", "ONLINE" if tg_ok else "OFFLINE/UNCONFIGURED"))
    
    # 5. Pollinations.ai Image API
    poll_ok = False
    try:
        req = urllib.request.Request("https://image.pollinations.ai/models", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            poll_ok = response.status == 200
    except Exception:
        pass
    checks.append(("Pollinations.ai Free Image API", "ONLINE" if poll_ok else "UNREACHABLE"))
    
    # In kết quả
    for name, status in checks:
        icon = "🟢" if status in ("OK", "CONNECTED", "ONLINE") or "CONFIGURED" in status else "🔴"
        print(f"{icon} {name:35s} | {status}")
        
    print("=" * 60)
    all_passed = all(s in ("OK", "CONNECTED", "ONLINE") or "CONFIGURED" in s for _, s in checks)
    if all_passed:
        print("✅ TOÀN BỘ HỆ THỐNG SẴN SÀNG CHO WORKFLOW 24/7!")
    else:
        print("⚠️ CÓ MỘT SỐ DỊCH VỤ CHƯA SẴN SÀNG. VUI LÒNG KIỂM TRA LẠI .ENV NẾU CẦN.")
    print("=" * 60)
    return all_passed

if __name__ == "__main__":
    run_health_check()
