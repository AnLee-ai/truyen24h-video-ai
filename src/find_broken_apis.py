import sys
import requests
from src import config, key_rotator

def check_gemini_key(key: str) -> tuple[bool, str]:
    """Test a single Gemini API key."""
    if not key:
        return False, "Empty Key"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={key}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": "hi"}]}]}
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            return True, "200 OK (VALID)"
        else:
            err_msg = res.json().get("error", {}).get("message", res.text[:80])
            return False, f"{res.status_code} ({err_msg})"
    except Exception as e:
        return False, str(e)[:60]

def check_groq_key(key: str) -> tuple[bool, str]:
    """Test a single Groq API key."""
    if not key:
        return False, "Empty Key"
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            return True, "200 OK (VALID)"
        else:
            err_msg = res.json().get("error", {}).get("message", res.text[:80])
            return False, f"{res.status_code} ({err_msg})"
    except Exception as e:
        return False, str(e)[:60]

def run_api_audit():
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=" * 70)
    print("ðŸ” AUDIT & DIAGNOSTIC: KIá»‚M TRA TOÃ€N Bá»˜ CÃC KHÃ“A API Há»† THá»NG")
    print("=" * 70)
    
    # 1. Audit Gemini Keys
    gemini_keys = key_rotator.gemini_rotator.keys
    print(f"\nðŸ“Œ [1] KIá»‚M TRA GEMINI API KEYS (Tá»•ng cá»™ng: {len(gemini_keys)} khÃ³a):")
    if not gemini_keys:
        print("  âŒ KhÃ´ng tÃ¬m tháº¥y khÃ³a GEMINI_API_KEY / GEMINI_API_KEYS nÃ o trong mÃ´i trÆ°á»ng!")
    else:
        for idx, k in enumerate(gemini_keys):
            mask = f"...{k[-6:]}" if len(k) >= 6 else k
            valid, msg = check_gemini_key(k)
            icon = "âœ… OK" if valid else "âŒ ERRROR 401"
            print(f"  - Key #{idx+1} [{mask:15s}]: {icon} | Status: {msg}")

    # 2. Audit Groq Keys
    groq_keys = key_rotator.groq_rotator.keys
    print(f"\nðŸ“Œ [2] KIá»‚M TRA GROQ API KEYS (Tá»•ng cá»™ng: {len(groq_keys)} khÃ³a):")
    if not groq_keys:
        print("  âš ï¸ KhÃ´ng cáº¥u hÃ¬nh khÃ³a GROQ_API_KEY / GROQ_API_KEYS (Há»‡ thá»‘ng dÃ¹ng Gemini).")
    else:
        for idx, k in enumerate(groq_keys):
            mask = f"...{k[-6:]}" if len(k) >= 6 else k
            valid, msg = check_groq_key(k)
            icon = "âœ… OK" if valid else "âŒ ERROR 401"
            print(f"  - Key #{idx+1} [{mask:15s}]: {icon} | Status: {msg}")

    # 3. Audit Supabase
    print("\nðŸ“Œ [3] KIá»‚M TRA Káº¾T Ná»I SUPABASE DATABASE:")
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        try:
            r = requests.get(f"{config.SUPABASE_URL}/rest/v1/", headers={"apikey": config.SUPABASE_KEY}, timeout=10)
            if r.status_code in (200, 404):
                print("  âœ… Supabase URL & Key: HOáº T Äá»˜NG Tá»T (200 OK)")
            else:
                print(f"  âŒ Supabase Lá»—i: Status {r.status_code} - {r.text[:80]}")
        except Exception as e:
            print(f"  âŒ Supabase Lá»—i káº¿t ná»‘i: {e}")
    else:
        print("  âŒ Thiáº¿u SUPABASE_URL hoáº·c SUPABASE_KEY!")

    # 4. Audit Telegram Bot API
    print("\nðŸ“Œ [4] KIá»‚M TRA TELEGRAM BOT API & CHANNEL:")
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                bot_name = r.json().get("result", {}).get("username", "Unknown")
                print(f"  âœ… Telegram Bot: HOáº T Äá»˜NG Tá»T (@{bot_name}) | Channel: {config.TELEGRAM_CHAT_ID}")
            else:
                print(f"  âŒ Telegram Bot Token lá»—i: Status {r.status_code} - {r.text[:80]}")
        except Exception as e:
            print(f"  âŒ Telegram Lá»—i káº¿t ná»‘i: {e}")
    else:
        print("  âŒ Thiáº¿u TELEGRAM_BOT_TOKEN hoáº·c TELEGRAM_CHAT_ID!")

    # 5. Audit Pollinations Free Image API
    print("\nðŸ“Œ [5] KIá»‚M TRA POLLINATIONS FREE IMAGE API:")
    try:
        r = requests.get("https://image.pollinations.ai/prompt/test", timeout=10)
        if r.status_code == 200:
            print("  âœ… Pollinations Image API: HOáº T Äá»˜NG Tá»T (200 OK)")
        else:
            print(f"  âš ï¸ Pollinations Image API Cáº£nh bÃ¡o: Status {r.status_code}")
    except Exception as e:
        print(f"  âŒ Pollinations Lá»—i káº¿t ná»‘i: {e}")

    print("=" * 70)

if __name__ == "__main__":
    run_api_audit()

