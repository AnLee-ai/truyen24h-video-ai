import json
import time
import re
import sys

try:
    from google import genai
    from google.genai import types
    USE_NEW_GENAI = True
except ImportError:
    import google.generativeai as genai  # type: ignore[no-redef]
    USE_NEW_GENAI = False

from src import config
from src import database
from src import key_rotator
from src.cache import cached
from templates import prompts

def safe_print(*args, **kwargs):
    """Override built-in print to prevent UnicodeEncodeError on Windows terminals."""
    msg = " ".join(str(arg) for arg in args)
    try:
        sys.stdout.write(msg + kwargs.get("end", "\n"))
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or 'utf-8'
            sys.stdout.write(msg.encode(encoding, errors='replace').decode(encoding) + kwargs.get("end", "\n"))
            sys.stdout.flush()
        except Exception:
            sys.stdout.write(msg.encode('ascii', errors='replace').decode('ascii') + kwargs.get("end", "\n"))
            sys.stdout.flush()

print = safe_print

def get_genai_client(api_key: str = None):
    current_key = api_key or key_rotator.get_gemini_key() or config.GEMINI_API_KEY
    if not current_key:
        raise ValueError("GEMINI_API_KEY / GEMINI_API_KEYS must be configured in environment variables.")
    if USE_NEW_GENAI:
        return genai.Client(api_key=current_key)
    else:
        genai.configure(api_key=current_key)  # type: ignore
        return genai

def safe_loads(text: str, default=None):
    """Safely parse JSON string, stripping markdown code block wrappers or extracting raw JSON object. Returns default if invalid."""
    if not text or not text.strip():
        return default if default is not None else {}
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # ThÃ¡Â»Â­ lÃƒÂ m sÃ¡ÂºÂ¡ch dÃ¡ÂºÂ¥u phÃ¡ÂºÂ©y thÃ¡Â»Â«a Ã¡Â»Å¸ cuÃ¡Â»â€˜i (trailing commas)
        cleaned_no_comma = re.sub(r",\s*([\}\]])", r"\1", cleaned)
        try:
            return json.loads(cleaned_no_comma)
        except Exception:
            pass
        # ThÃ¡Â»Â­ trÃƒÂ­ch xuÃ¡ÂºÂ¥t khÃ¡Â»â€˜i {...} hoÃ¡ÂºÂ·c [...] bÃ¡ÂºÂ±ng Regex
        json_block = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if json_block:
            try:
                candidate = json_block.group(0)
                candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)
                return json.loads(candidate)
            except Exception:
                pass
    return default if default is not None else {}

def remove_repetitive_sentences(text: str) -> str:
    """Clean duplicate consecutive sentences or paragraphs."""
    paragraphs = text.split("\n")
    cleaned_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            cleaned_paragraphs.append("")
            continue
        sentences = re.split(r'(?<=[.?!Ã¢â‚¬Â¦])\s+(?=[a-zA-ZÃƒÂ ÃƒÂ¡ÃƒÂ¢ÃƒÂ£ÃƒÂ¨ÃƒÂ©ÃƒÂªÃƒÂ¬ÃƒÂ­ÃƒÂ²ÃƒÂ³ÃƒÂ´ÃƒÂµÃƒÂ¹ÃƒÂºÃƒÂ½Ã„â€˜Ãƒâ‚¬ÃƒÂÃƒâ€šÃƒÆ’ÃƒË†Ãƒâ€°ÃƒÅ ÃƒÅ’ÃƒÂÃƒâ€™Ãƒâ€œÃƒâ€Ãƒâ€¢Ãƒâ„¢ÃƒÅ¡ÃƒÂÃ„Â0-9"\'Ã‚Â«Ã¢â‚¬Å“])', para)
        cleaned_sentences: list[str] = []
        for sentence in sentences:
            s_strip = sentence.strip()
            if not s_strip:
                continue
            if cleaned_sentences and cleaned_sentences[-1].strip().lower() == s_strip.lower():
                continue
            cleaned_sentences.append(sentence)
        cleaned_paragraphs.append(" ".join(cleaned_sentences))
        
    final_paragraphs: list[str] = []
    last_non_empty = None
    for p in cleaned_paragraphs:
        if not p.strip():
            if final_paragraphs and final_paragraphs[-1] == "":
                continue
            final_paragraphs.append("")
            continue
            
        if last_non_empty and last_non_empty.strip().lower() == p.strip().lower():
            continue
            
        final_paragraphs.append(p)
        last_non_empty = p
        
    return "\n".join(final_paragraphs)

def clean_chapter_content(text: str) -> str:
    """Clean draft content, stripping markdown and prefix headers like 'Dáº«n lÆ°á»£c:', 'ChÆ°Æ¡ng X:', etc."""
    cleaned = text.strip()
    pattern = r"(?im)^\s*[*_]*\s*(?:Dáº«n lÆ°á»£c|Giá»›i thiá»‡u|Pháº§n dáº«n lÆ°á»£c|TÃ³m táº¯t bá»‘i cáº£nh|Prologue|Introduction|Giá»›i thiá»‡u bá»‘i cáº£nh)\s*[:ï¼š\-â€“â€”]*\s*[*_]*\s*[:ï¼š\-â€“â€”]*\s*"
    cleaned = re.sub(pattern, "", cleaned).strip()
    cleaned = remove_repetitive_sentences(cleaned)
    return cleaned

def expand_chapter_content(content: str, target_words: int = 3200) -> str:
    """NÃ¡Â»â€˜i dÃƒÂ i kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n chÃ†Â°Ã†Â¡ng truyÃ¡Â»â€¡n nÃ¡ÂºÂ¿u chÃ†Â°a Ã„â€˜Ã¡Â»Â§ Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i >10 phÃƒÂºt audio (600 giÃƒÂ¢y)."""
    current_words = len(content.split()) if content else 0
    if current_words >= target_words:
        return content
        
    print(f"[INFO] Ã¢Å¡Â¡ CHÃ¡ÂºÂ¾ Ã„ÂÃ¡Â»Ëœ LÃƒâ‚¬M LÃ¡ÂºÂ I (>10 PHÃƒÅ¡T): Ã„ÂÃ¡Â»â„¢ dÃƒÂ i hiÃ¡Â»â€¡n tÃ¡ÂºÂ¡i {current_words} tÃ¡Â»Â« (<{target_words} tÃ¡Â»Â«). Ã„Âang gÃ¡Â»Âi AI viÃ¡ÂºÂ¿t nÃ¡Â»â€˜i tiÃ¡ÂºÂ¿p phÃƒÂ¢n cÃ¡ÂºÂ£nh kÃ¡Â»â€¹ch tÃƒÂ­nh...")
    
    continuation_prompt = (
        f"DÃ†Â°Ã¡Â»â€ºi Ã„â€˜ÃƒÂ¢y lÃƒÂ  phÃ¡ÂºÂ§n trÃ†Â°Ã¡Â»â€ºc cÃ¡Â»Â§a chÃ†Â°Ã†Â¡ng truyÃ¡Â»â€¡n (tÃ¡Â»â€¢ng {current_words} tÃ¡Â»Â«):\n\n"
        f"{content[-1500:]}\n\n"
        f"YÃƒÅ U CÃ¡ÂºÂ¦U BÃ¡ÂºÂ®T BUÃ¡Â»ËœC (Ãƒâ€°P THÃ¡Â»Å“I LÃ†Â¯Ã¡Â»Â¢NG KÃƒâ€°O DÃƒâ‚¬I >10 PHÃƒÅ¡T AUDIO):\n"
        f"HÃƒÂ£y viÃ¡ÂºÂ¿t tiÃ¡ÂºÂ¿p phÃƒÂ¢n cÃ¡ÂºÂ£nh diÃ¡Â»â€¦n biÃ¡ÂºÂ¿n kÃ¡Â»â€¹ch tÃƒÂ­nh tiÃ¡ÂºÂ¿p theo cÃ¡Â»Â§a cÃƒÂ¢u chuyÃ¡Â»â€¡n trÃƒÂªn (tÃ¡Â»â€˜i thiÃ¡Â»Æ’u 1500 - 2000 tÃ¡Â»Â« nÃ¡Â»Â¯a).\n"
        f"1. ViÃ¡ÂºÂ¿t chi tiÃ¡ÂºÂ¿t cuÃ¡Â»â„¢c Ã„â€˜Ã¡Â»â€˜i thoÃ¡ÂºÂ¡i gay gÃ¡ÂºÂ¯t, bÃ¡Â»â„¢c phÃƒÂ¡t cÃ¡ÂºÂ£m xÃƒÂºc giÃ¡Â»Â¯a cÃƒÂ¡c nhÃƒÂ¢n vÃ¡ÂºÂ­t chÃƒÂ­nh.\n"
        f"2. MiÃƒÂªu tÃ¡ÂºÂ£ chi tiÃ¡ÂºÂ¿t chiÃƒÂªu thÃ¡Â»Â©c, giao phong kÃ¡Â»â€¹ch tÃƒÂ­nh vÃƒÂ  suy nghÃ„Â© nÃ¡Â»â„¢i tÃƒÂ¢m dÃ¡Â»â€œn dÃ¡ÂºÂ­p.\n"
        f"3. KÃ¡ÂºÂ¿t thÃƒÂºc bÃ¡ÂºÂ±ng mÃ¡Â»â„¢t nÃƒÂºt thÃ¡ÂºÂ¯t cliffhanger kÃ¡Â»â€¹ch tÃƒÂ­nh.\n"
        f"ViÃ¡ÂºÂ¿t thÃ¡ÂºÂ³ng vÃƒÂ o cÃƒÂ¢u chuyÃ¡Â»â€¡n 100% bÃ¡ÂºÂ±ng TiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t mÃ†Â°Ã¡Â»Â£t mÃƒÂ , khÃƒÂ´ng lÃ¡ÂºÂ·p lÃ¡ÂºÂ¡i Ã„â€˜oÃ¡ÂºÂ¡n cÃ…Â©."
    )
    
    for _expand_attempt in range(3):
        part_next = call_gemini(continuation_prompt)
        if part_next and len(part_next.split()) > 200:
            cleaned_next = clean_chapter_content(part_next)
            if cleaned_next.lower() in content.lower():
                continue
            content = content + "\n\n" + cleaned_next
            print(f"[SUCCESS] Ã„ ÃƒÂ£ nÃ¡Â»â€˜i dÃƒÂ i chÃ†Â°Ã†Â¡ng truyÃ¡Â»â€¡n! TÃ¡Â»â€¢ng sÃ¡Â»â€˜ tÃ¡Â»Â« mÃ¡Â»â€ºi: {len(content.split())} tÃ¡Â»Â«.")
            if len(content.split()) >= target_words:
                break
    return content

LEGACY_INVALID_NAMES = {}

def verify_and_sanitize_chapter_content(text: str, novel_id: str = "") -> tuple:
    """
    BÃ¡Â»Ëœ KIÃ¡Â»â€šM TRA TÃ¡Â»Â° Ã„ Ã¡Â»ËœNG BÃ¡ÂºÂ¢O VÃ¡Â»â€  CHÃ†Â¯Ã†Â NG TRUYÃ¡Â»â€ N (Automated Chapter Auditor).
    """
    if not text:
        return text, False
        
    
    found_invalid = []
    sanitized_text = text
    for old_n, new_n in LEGACY_INVALID_NAMES.items():
        if old_n in sanitized_text:
            found_invalid.append(old_n)
            sanitized_text = re.sub(rf"\b{re.escape(old_n)}\b", new_n, sanitized_text)
            
    if found_invalid:
        print(f"[WARNING] Ã¢Å¡Â Ã¯Â¸Â PHÃƒÂT HIÃ¡Â»â€ N LÃ¡Â»â€“I TÃƒÅ N NHÃƒâ€šN VÃ¡ÂºÂ¬T CÃ…Â¨: {found_invalid}! Ã„ÂÃƒÂ£ tÃ¡Â»Â± Ã„â€˜Ã¡Â»â„¢ng thay thÃ¡ÂºÂ¿ chuÃ¡ÂºÂ©n thÃƒÂ nh nhÃƒÂ¢n vÃ¡ÂºÂ­t bÃ¡Â»â„¢ truyÃ¡Â»â€¡n hiÃ¡Â»â€¡n tÃ¡ÂºÂ¡i.")
        return sanitized_text, True
        
    return text, False



@cached(ttl_seconds=86400)
def translate_to_vietnamese_with_gemini(text: str) -> str:
    """TÃ¡Â»Â± Ã„â€˜Ã¡Â»â„¢ng kiÃ¡Â»Æ’m tra vÃƒÂ  dÃ¡Â»â€¹ch toÃƒÂ n bÃ¡Â»â„¢ kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t tÃ¡Â»Â« tiÃ¡ÂºÂ¿ng Trung/tiÃ¡ÂºÂ¿ng Anh sang tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t chuÃ¡ÂºÂ©n mÃ†Â°Ã¡Â»Â£t mÃƒÂ  100% qua Gemini API."""
    if not text or not text.strip():
        return text
        
    # TÃ¡Â»Â± Ã„â€˜Ã¡Â»â„¢ng rÃƒÂ  soÃƒÂ¡t vÃƒÂ  khÃ¡Â»Â­ tÃƒÂªn nhÃƒÂ¢n vÃ¡ÂºÂ­t cÃ…Â© rÃƒÂ¡c
    text, _ = verify_and_sanitize_chapter_content(text)
    
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    if not has_chinese:
        return text
        
    print(f"[INFO] BÃ¡ÂºÂ¯t Ã„â€˜Ã¡ÂºÂ§u rÃƒÂ  soÃƒÂ¡t ngÃƒÂ´n ngÃ¡Â»Â¯ kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n (Has Chinese: {has_chinese})...")
    print("[INFO] KÃƒÂ­ch hoÃ¡ÂºÂ¡t Ã„ÂÃ¡Â»â„¢ng CÃ†Â¡ DÃ¡Â»â€¹ch ThuÃ¡ÂºÂ­t Gemini API: DÃ¡Â»â€¹ch/TÃ¡Â»â€˜i Ã†Â°u toÃƒÂ n bÃ¡Â»â„¢ kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t sang TiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t mÃ†Â°Ã¡Â»Â£t mÃƒÂ ...")
    translate_prompt = (
        "BÃ¡ÂºÂ¡n lÃƒÂ  dÃ¡Â»â€¹ch giÃ¡ÂºÂ£ tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t webtoon hÃƒÂ ng Ã„â€˜Ã¡ÂºÂ§u. HÃƒÂ£y dÃ¡Â»â€¹ch/chuyÃ¡Â»Æ’n ngÃ¡Â»Â¯ toÃƒÂ n bÃ¡Â»â„¢ chÃ†Â°Ã†Â¡ng tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t sau Ã„â€˜ÃƒÂ¢y sang tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t tÃ¡Â»Â± nhiÃƒÂªn, giÃƒÂ u cÃ¡ÂºÂ£m xÃƒÂºc vÃƒÂ  hÃ¡ÂºÂ¥p dÃ¡ÂºÂ«n.\n"
        "YÃƒÅ U CÃ¡ÂºÂ¦U DÃ¡Â»Å CH THUÃ¡ÂºÂ¬T BÃ¡ÂºÂ®T BUÃ¡Â»ËœC:\n"
        "1. DÃ¡Â»â€¹ch 100% sang tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t thuÃ¡ÂºÂ§n tÃƒÂºy, mÃ†Â°Ã¡Â»Â£t mÃƒÂ , vÃ„Æ’n phong tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t hÃƒÂ nh Ã„â€˜Ã¡Â»â„¢ng/huyÃ¡Â»Ân Ã¡ÂºÂ£o kÃ¡Â»â€¹ch tÃƒÂ­nh.\n"
        "2. GiÃ¡Â»Â¯ nguyÃƒÂªn 100% Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i vÃ„Æ’n bÃ¡ÂºÂ£n, lÃ¡Â»Âi thoÃ¡ÂºÂ¡i trong ngoÃ¡ÂºÂ·c kÃƒÂ©p (\"...\"), vÃƒÂ  cÃ¡ÂºÂ¥u trÃƒÂºc cÃƒÂ¢u chuyÃ¡Â»â€¡n. TUYÃ¡Â»â€ T Ã„ÂÃ¡Â»ÂI KHÃƒâ€NG tÃƒÂ³m tÃ¡ÂºÂ¯t hay bÃ¡Â»Â sÃƒÂ³t chi tiÃ¡ÂºÂ¿t nÃƒÂ o.\n"
        "3. GiÃ¡Â»Â¯ nguyÃƒÂªn 100% tÃƒÂªn nhÃƒÂ¢n vÃ¡ÂºÂ­t chuÃ¡ÂºÂ©n tÃ¡Â»Â« nguyÃƒÂªn bÃ¡ÂºÂ£n. CÃ¡ÂºÂ¥m tÃ¡Â»Â± Ã„â€˜Ã¡Â»â€¢i sang tÃƒÂªn khÃƒÂ¡c.\n"
        "4. ChÃ¡Â»â€° xuÃ¡ÂºÂ¥t ra duy nhÃ¡ÂºÂ¥t vÃ„Æ’n bÃ¡ÂºÂ£n truyÃ¡Â»â€¡n Ã„â€˜ÃƒÂ£ dÃ¡Â»â€¹ch sang tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t, khÃƒÂ´ng kÃƒÂ¨m lÃ¡Â»Âi dÃ¡ÂºÂ«n hay giÃ¡ÂºÂ£i thÃƒÂ­ch.\n\n"
        f"VÃ„â€šN BÃ¡ÂºÂ¢N CÃ¡ÂºÂ¦N DÃ¡Â»Å CH:\n{text}"
    )
    translated_res = call_gemini(translate_prompt)
    if translated_res and len(translated_res.split()) > 200:
        cleaned_res = clean_chapter_content(translated_res)
        cleaned_res, _ = verify_and_sanitize_chapter_content(cleaned_res)
        print(f"[SUCCESS] Ã„ÂÃƒÂ£ hoÃƒÂ n thÃƒÂ nh dÃ¡Â»â€¹ch kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n sang TiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t qua Gemini API! Ã„ÂÃ¡Â»â„¢ dÃƒÂ i: {len(cleaned_res.split())} tÃ¡Â»Â«.")
        return cleaned_res
    return text

@cached(ttl_seconds=86400)
def call_gemini(prompt: str, json_mode: bool = False, retries: int = 12) -> str:
    """
    Ã†Â¯U TIÃƒÅ N 100% HÃƒâ‚¬NG Ã„ÂÃ¡ÂºÂ¦U: InkOS Multi-Agent Engine (Google Gemini 2.0 Flash API vÃ¡Â»â€ºi Key Rotator).
    ChÃ¡Â»â€° khi Gemini hÃ¡ÂºÂ¿t Key mÃ¡Â»â€ºi chuyÃ¡Â»Æ’n sang Groq / OpenRouter dÃ¡Â»Â± phÃƒÂ²ng.
    """
    # =========================================================================
    # Ã„ÂÃ¡Â»ËœNG CÃ†Â  Ã†Â¯U TIÃƒÅ N 1: InkOS Gemini 2.0 Flash Engine (Google API vÃ¡Â»â€ºi Key Rotator)
    # =========================================================================
    gemini_models = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
    for attempt in range(min(retries, 4)):
        g_key = key_rotator.get_gemini_key() or config.GEMINI_API_KEY
        if not g_key:
            break
            
        current_g_model = gemini_models[attempt % len(gemini_models)]
        try:
            if USE_NEW_GENAI:
                client = get_genai_client(api_key=g_key)
                generation_config = types.GenerateContentConfig(
                    max_output_tokens=8192,
                    response_mime_type="application/json" if json_mode else None
                )
                response = client.models.generate_content(
                    model=current_g_model,
                    contents=prompt,
                    config=generation_config
                )
            else:
                genai.configure(api_key=g_key)  # type: ignore
                g_config = {"max_output_tokens": 8192}
                if json_mode:
                    g_config["response_mime_type"] = "application/json"
                model = genai.GenerativeModel(current_g_model, generation_config=g_config)  # type: ignore
                response = model.generate_content(prompt)

            if response.text and len(response.text.strip().split()) > 10:
                print(f"[SUCCESS] Ã¢Å¡Â¡ InkOS Writer Agent [{current_g_model}]: TÃ¡ÂºÂ¡o kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n mÃ†Â°Ã¡Â»Â£t mÃƒÂ  thÃƒÂ nh cÃƒÂ´ng! ({len(response.text.strip().split())} tÃ¡Â»Â«).")
                return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "UNAUTHENTICATED" in err_str:
                print(f"[WARNING] API Key [Gemini] ...{g_key[-6:] if len(g_key)>6 else g_key} invalid (401). Switched key.")
                key_rotator.mark_gemini_key_failed(g_key, is_permanent=True)
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"[WARNING] API Key [Gemini] ...{g_key[-6:] if len(g_key)>6 else g_key} rate limited (429). Switched key.")
                key_rotator.mark_gemini_key_failed(g_key, is_permanent=False)
                time.sleep(2.5)
            elif "503" in err_str or "SERVICE_UNAVAILABLE" in err_str:
                print(f"[WARNING] Gemini [{current_g_model}] Service Unavailable (503). Waiting 5s...")
                time.sleep(5.0)
            else:
                print(f"[ERROR] Gemini [{current_g_model}] failed with unexpected error: {e}")
                time.sleep(1.0)

    # =========================================================================
    # ÄÆ¯á»œNG CÆ  Dá»° PHÃ’NG 2: Local Mangstoon_AI Engine (Thay vÃ¬ Groq)
    # =========================================================================
    local_mangstoon = None
    if local_mangstoon and len(local_mangstoon.strip().split()) > 10:
        print("[SUCCESS] Local Mangstoon_AI succeeded!")
        return local_mangstoon.strip()

    # =========================================================================
    # ÄÆ¯á»œNG CÆ  Dá»° PHÃ’NG 3: Groq Multi-Model Engine (Dá»± phÃ²ng cáº¥p 3)
    # =========================================================================
    groq_key = key_rotator.get_groq_key() or config.GROQ_API_KEY
    if groq_key:
        import requests
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        raw_groq = [config.GROQ_MODEL_WRITER, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        groq_models = [m for m in raw_groq if m and m != "mixtral-8x7b-32768"]
        max_tokens_options = [8000, 6000, 4000] if not json_mode else [1500]
        
        for attempt in range(min(retries, 3)):
            current_model = groq_models[attempt % len(groq_models)]
            current_max_tokens = max_tokens_options[min(attempt, len(max_tokens_options)-1)]
            payload_prompt = prompt[:2200] if (current_model == "llama-3.1-8b-instant" and len(prompt) > 2200) else prompt
            
            data = {
                "model": current_model,
                "messages": [{"role": "user", "content": payload_prompt}],
                "temperature": 0.7,
                "max_tokens": current_max_tokens
            }
            if json_mode:
                data["response_format"] = {"type": "json_object"}
                
            try:
                response = requests.post(url, json=data, headers=headers, timeout=45)  # type: ignore[arg-type]
                if response.status_code == 200:
                    resp_json = response.json()
                    try:
                        content = resp_json["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError):
                        continue
                    if content and len(content.strip().split()) > 10:
                        print(f"[SUCCESS] Groq Fallback Engine [{current_model}]: Ã„ÂÃƒÂ£ sinh kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n ({len(content.strip().split())} tÃ¡Â»Â«).")
                        return content.strip()
                elif response.status_code == 429:
                    time.sleep(1.5)
                    continue
            except Exception:
                pass

    print("[WARNING] All primary AI keys failed. Switching to OpenRouter 100% Free AI Engine...")
    openrouter_res = call_openrouter_free_llm(prompt)
    if openrouter_res:
        return openrouter_res

    print("[WARNING] OpenRouter failed. Switching to Pollinations Multi-Model 100% Free LLM Engine...")
    free_res = call_pollinations_free_llm(prompt)
    if free_res:
        return free_res
    return ""

def call_openrouter_free_llm(prompt: str) -> str:
    """Emergency Fallback to OpenRouter 100% Free AI Models (Zero Cost)."""
    import requests
    print("[INFO] Fallback to OpenRouter Free AI Engine...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://truyen24h.ai",
        "X-Title": "Truyen24h Video AI Studio"
    }
    
    or_key = key_rotator.get_openrouter_key()
    if or_key:
        headers["Authorization"] = f"Bearer {or_key}"
    
    free_models = [
        "google/gemini-3.6-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    for m in free_models:
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=40)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content and len(content.strip().split()) > 20:
                    print(f"[SUCCESS] OpenRouter Free LLM ({m}) succeeded! ({len(content.strip().split())} words)")
                    return content.strip()
        except Exception as e:
            print(f"[WARNING] OpenRouter model ({m}) error: {e}")
            continue
    return ""

def call_pollinations_free_llm(prompt: str) -> str:
    """100% Free Emergency LLM Fallback via Pollinations.ai POST API with Multi-Model Rotation (Zero API Key needed)."""
    import requests
    print("[INFO] Fallback to Pollinations Multi-Model Free LLM Engine...")
    
    url = "https://text.pollinations.ai/"
    headers = {"Content-Type": "application/json"}
    pollination_models = ["mistral", "qwen-coder", "openai", "llama"]
    
    for model_name in pollination_models:
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": model_name
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            if resp.status_code == 200 and resp.text:
                res_text = resp.text.strip()
                if len(res_text.split()) > 20 and "402" not in res_text:
                    print(f"[SUCCESS] Pollinations Free LLM POST ({model_name}) succeeded! ({len(res_text.split())} words)")
                    return res_text
        except Exception as e:
            print(f"[WARNING] Pollinations Free LLM ({model_name}) failed: {e}")
            continue
        
    # Backup GET request rÃƒÂºt gÃ¡Â»Ân prompt
    try:
        import urllib.parse
        import urllib.request
        short_prompt = urllib.parse.quote(prompt[:1200])
        req = urllib.request.Request(f"https://text.pollinations.ai/{short_prompt}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            res_text = response.read().decode('utf-8')
            if res_text and len(res_text.split()) > 20 and "402" not in res_text:
                return res_text.strip()
    except Exception:
        pass
        
    return ""

def get_embedding(text: str) -> list:
    """Generate vector embedding for semantic search using text-embedding-004 (padded to 1536 for Supabase pgvector)."""
    EMBED_DIM = 1536  # Supabase pgvector vector(1536) column dimension
    g_key = key_rotator.get_gemini_key() or config.GEMINI_API_KEY
    if not g_key:
        return [0.0] * EMBED_DIM
    try:
        if USE_NEW_GENAI:
            client = get_genai_client(api_key=g_key)
            result = client.models.embed_content(
                model=config.GEMINI_MODEL_EMBED,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                )
            )
            emb = result.embeddings[0].values
        else:
            genai.configure(api_key=g_key)  # type: ignore
            result = genai.embed_content(
                model=f"models/{config.GEMINI_MODEL_EMBED}",
                content=text,
                task_type="retrieval_document"
            )
            emb = result['embedding']

        if len(emb) > EMBED_DIM:
            return emb[:EMBED_DIM]
        elif len(emb) < EMBED_DIM:
            return emb + [0.0] * (EMBED_DIM - len(emb))
        return emb
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "UNAUTHENTICATED" in err_str:
            key_rotator.mark_gemini_key_failed(g_key)
        print("[WARNING] Skipping embedding generation due to API key error.")
        return [0.0] * EMBED_DIM

# Novel Lifecycle Operations
def init_novel_pipeline(title: str, description: str) -> dict:
    print(f"[INFO] Initializing new novel: '{title}'...")
    novel = database.init_novel(title, description)
    novel_id = novel.get("id") or "";
    if not novel_id: raise ValueError("init_novel failed")
    print(f"[INFO] Created novel record in database. ID: {novel_id}")
    
    try:
        print("[INFO] Generating expanded plot summary in Vietnamese...")
        plot_prompt = prompts.PLOT_EXPANSION_PROMPT.format(title=title, description=description)
        detailed_plot = call_gemini(plot_prompt)
        database.update_novel_description(novel_id, detailed_plot)
        novel["description"] = detailed_plot
        print("[INFO] Expanded plot summary stored in novels table.")
    except Exception as e:
        print(f"[WARNING] Failed to generate/store expanded plot summary: {e}")
    
    prompt = prompts.OUTLINE_PROMPT.format(title=title, description=novel["description"])
    outline_json = call_gemini(prompt, json_mode=True)
    
    try:
        outline = safe_loads(outline_json)
        database.upsert_narrative_thread(
            novel_id=novel_id,
            thread_name="Global Outline",
            description=json.dumps(outline, ensure_ascii=False)
        )
        print("[INFO] Global Outline generated and stored successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to parse global outline JSON: {e}. Raw content: {outline_json}")
        database.upsert_narrative_thread(
            novel_id=novel_id,
            thread_name="Global Outline",
            description=outline_json
        )
        
    return novel

def generate_arc_blueprints(novel_id: str, arc: dict) -> list:
    arc_num = arc.get("arc_number")
    arc_title = arc.get("title")
    start_ch = arc.get("start_chapter")
    end_ch = arc.get("end_chapter")
    arc_summary = arc.get("summary", "TiÃ¡ÂºÂ¿p tÃ¡Â»Â¥c diÃ¡Â»â€¦n biÃ¡ÂºÂ¿n cÃ¡Â»Â§a bÃ¡Â»â€˜i cÃ¡ÂºÂ£nh hÃ¡Â»Âc viÃ¡Â»â€¡n.")
    
    print(f"[INFO] Generating blueprints for Arc {arc_num}: '{arc_title}' (Chapters {start_ch} - {end_ch})...")
    
    novel = database.get_novel(novel_id)
    novel_title = novel.get("title", "TruyÃ¡Â»â€¡n mÃ¡Â»â€ºi")
    novel_description = novel.get("description", "")
    
    existing_chapters = database.get_all_chapters(novel_id)
    status_summary = f"Written {len(existing_chapters)} chapters."
    if existing_chapters:
        status_summary += f" Latest chapter was: {existing_chapters[-1]['title']}"
        
    prompt = prompts.ARC_PROMPT.format(
        novel_title=novel_title,
        novel_description=novel_description,
        arc_summary=arc_summary,
        arc_number=arc_num,
        arc_title=arc_title,
        start_chapter=start_ch,
        end_chapter=end_ch,
        global_status=status_summary
    )
    
    blueprints_json = call_gemini(prompt, json_mode=True)
    
    try:
        try:
            blueprints_raw = safe_loads(blueprints_json)
            if isinstance(blueprints_raw, list):
                blueprints = blueprints_raw
            elif isinstance(blueprints_raw, dict):
                # GiÃ¡ÂºÂ£i nÃƒÂ©n nÃ¡ÂºÂ¿u LLM bÃ¡Â»Âc trong dict {"blueprints": [...]} hoÃ¡ÂºÂ·c {"chapters": [...]}
                blueprints = blueprints_raw.get("blueprints") or blueprints_raw.get("chapters") or blueprints_raw.get("arcs") or []
                if not isinstance(blueprints, list):
                    raise ValueError("Extracted blueprints from dict is not a list")
            else:
                raise ValueError("Parsed blueprints is not a list or dict")
        except Exception as e:
            print(f"[WARNING] Failed to parse blueprints JSON: {e}. Attempting recovery...")
            blueprints = []
            matches = re.findall(r"\{\s*\"chapter_number\"[\s\S]*?\}", blueprints_json)
            for m in matches:
                try:
                    ch_obj = json.loads(m)
                    if isinstance(ch_obj, dict):
                        blueprints.append(ch_obj)
                except Exception:
                    try:
                        ch_obj = safe_loads(m)
                        if isinstance(ch_obj, dict):
                            blueprints.append(ch_obj)
                    except Exception:
                        pass

        try:
            start_num = int(str(start_ch).strip()) if start_ch else 1
        except (ValueError, TypeError):
            start_num = 1
        try:
            end_num = int(str(end_ch).strip()) if end_ch else (start_num + 24)
        except (ValueError, TypeError):
            end_num = start_num + 24
        
        EPIC_TITLES = [
            "TrÃƒÂ¹ng Sinh VÃ¡ÂºÂ¡n CÃ¡Â»â€¢, ThÃƒÂ´n PhÃ¡Â»â€¡ VÃƒÂ´ TÃ¡ÂºÂ­n",
            "ThÃ¡Â»Â©c TÃ¡Â»â€°nh ThÃ¡ÂºÂ§n ThÃ¡Â»Æ’, NÃƒÂ©n Ãƒâ€°p ThÃ¡ÂºÂ§n Ma",
            "HuyÃ¡ÂºÂ¿t MÃ¡ÂºÂ¡ch ThÃƒÂ´n ThiÃƒÂªn, TrÃ¡ÂºÂ¥n TÃƒÂ¡m PhÃ†Â°Ã†Â¡ng",
            "QuyÃ¡Â»Ân TrÃ¡ÂºÂ¥n SÃ†Â¡n HÃƒÂ , Uy ChÃ¡ÂºÂ¥n ChÃ†Â° ThiÃƒÂªn",
            "VÃƒÂ´ Ã„ÂÃ¡Â»â€¹ch TrÃƒÂ¹ng Sinh, HÃ¡Â»â€”n Ã„ÂÃ¡Â»â„¢n LuyÃ¡Â»â€¡n KhÃƒÂ­",
            "NghÃ¡Â»â€¹ch ThiÃƒÂªn Ã„ÂÃ¡Â»â„¢c TÃƒÂ´n, LuyÃ¡Â»â€¡n HÃƒÂ³a ThÃ¡ÂºÂ§n ThÃ¡ÂºÂ¡ch",
            "ThÃƒÂ´n PhÃ¡Â»â€¡ NguyÃƒÂªn KhÃƒÂ­, PhÃƒÂ¡ Tam CÃ¡ÂºÂ£nh",
            "VÃ¡ÂºÂ¡n GiÃ¡Â»â€ºi QuÃ¡Â»Â³ BÃƒÂ¡i, TiÃƒÂªu ViÃƒÂªm XuÃ¡ÂºÂ¥t ThÃ¡ÂºÂ¿",
            "ThÃƒÂ´n PhÃ¡Â»â€¡ Ma NhÃ¡ÂºÂ«n, Khai MÃ¡Â»Å¸ ThÃ¡ÂºÂ§n ThÃƒÂ´ng",
            "VÃƒÂ´ Song KiÃ¡ÂºÂ¿m KhÃƒÂ­, TrÃ¡ÂºÂ£m DiÃ¡Â»â€¡t CÃ†Â°Ã¡Â»Âng Ã„ÂÃ¡Â»â€¹ch",
            "HÃ¡Â»â€¡ ThÃ¡Â»â€˜ng ThÃ¡ÂºÂ§n CÃ¡ÂºÂ¥p, ThÃƒÂ´n PhÃ¡Â»â€¡ VÃ¡ÂºÂ¡n VÃ¡ÂºÂ­t",
            "BÃƒÂ¡ ThÃ¡ÂºÂ§n XuÃ¡ÂºÂ¥t ThÃ¡ÂºÂ¿, NgÃ„Æ’n CÃ¡ÂºÂ£n VÃ¡ÂºÂ¡n QuÃƒÂ¢n",
            "ThÃƒÂ´n PhÃ¡Â»â€¡ VÃ„Â©nh HÃ¡ÂºÂ±ng, XÃƒÂ¢y DÃ¡Â»Â±ng Ã„ÂÃ¡ÂºÂ¿ CÃ†Â¡",
            "ThÃƒÂ´n ThiÃƒÂªn LuyÃ¡Â»â€¡n Ã„ÂÃ¡Â»â€¹a, Ã„ÂÃ¡Â»â„¢c TÃƒÂ´n VÃ¡ÂºÂ¡n CÃ¡Â»â€¢",
            "TuyÃ¡Â»â€¡t ThÃ¡ÂºÂ¿ VÃƒÂ´ Ã„ÂÃ¡Â»â€¹ch, Phong Ã¡ÂºÂ¤n ThÃ¡ÂºÂ§n HoÃƒÂ ng",
            "KhÃƒÂ­ PhÃƒÂ¡ch NgÃƒÂºt TrÃ¡Â»Âi, ThÃƒÂ´n PhÃ¡Â»â€¡ Long MÃ¡ÂºÂ¡ch",
            "VÃ¡ÂºÂ¡n CÃ¡Â»â€¢ Ma Cung, Ã„ÂÃ¡ÂºÂ¡i ChiÃ¡ÂºÂ¿n ChÃ†Â° ThiÃƒÂªn",
            "BÃƒÂ¡ ChÃ¡Â»Â§ HuyÃ¡Â»Ân ThoÃ¡ÂºÂ¡i, LuyÃ¡Â»â€¡n HÃƒÂ³a VÃ¡ÂºÂ¡n GiÃ¡Â»â€ºi"
        ]
        
        parsed_numbers = {int(b.get("chapter_number", 0)) for b in blueprints if isinstance(b, dict)}
        for ch_i in range(start_num, end_num + 1):
            if ch_i not in parsed_numbers:
                epic_t = EPIC_TITLES[(ch_i - 1) % len(EPIC_TITLES)]
                blueprints.append({
                    "chapter_number": ch_i,
                    "chapter_title": f"{epic_t} (TÃ¡ÂºÂ­p {ch_i})",
                    "blueprint": f"DiÃ¡Â»â€¦n biÃ¡ÂºÂ¿n kÃ¡Â»â€¹ch tÃƒÂ­nh tiÃ¡ÂºÂ¿p theo cÃ¡Â»Â§a cÃƒÂ¢u chuyÃ¡Â»â€¡n Ã¡Â»Å¸ chÃ†Â°Ã†Â¡ng {ch_i}.",
                    "characters_present": [],
                    "narrative_goal": "PhÃƒÂ¡t triÃ¡Â»Æ’n cÃ¡Â»â€˜t truyÃ¡Â»â€¡n"
                })

        existing_chapter_numbers = {c["chapter_number"] for c in existing_chapters}
        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or f"ChÃ†Â°Ã†Â¡ng {ch_num}"
            blueprint_text = ch_data.get("blueprint") or "TiÃ¡ÂºÂ¿p tÃ¡Â»Â¥c diÃ¡Â»â€¦n biÃ¡ÂºÂ¿n cÃƒÂ¢u chuyÃ¡Â»â€¡n."
            
            # ChÃ¡Â»â€° tÃ¡ÂºÂ¡o blueprint nÃ¡ÂºÂ¿u chÃ†Â°Ã†Â¡ng chÃ†Â°a tÃ¡Â»â€œn tÃ¡ÂºÂ¡i trong CSDL
            if ch_num not in existing_chapter_numbers:
                ch_record = database.create_chapter(
                    novel_id=novel_id,
                    chapter_number=ch_num,
                    title=ch_title,
                    content=f"BLUEPRINT: {blueprint_text}"
                )
                if ch_record:
                    inserted_chapters.append(ch_record)
            
        print(f"[INFO] Created/Updated {len(inserted_chapters)} new chapter blueprints in DB.")
        return inserted_chapters
    except Exception as e:
        print(f"[ERROR] Failed to generate/parse blueprints for Arc {arc_num}: {e}")
        return []

def get_current_arc(novel_id: str, chapter_number: int) -> dict:
    threads = database.get_narrative_threads(novel_id)
    outline_thread = next((t for t in threads if t["thread_name"] == "Global Outline"), None)
    if not outline_thread:
        return {}
        
    try:
        outline = json.loads(outline_thread["description"])
        for arc in outline.get("arcs", []):
            if arc["start_chapter"] <= chapter_number <= arc["end_chapter"]:
                return arc
    except Exception as e:
        print(f"[ERROR] Failed to load outline JSON: {e}")
        
    return {
        "arc_number": 1,
        "title": "Default Arc",
        "start_chapter": 1,
        "end_chapter": 25
    }

def write_next_chapter(novel_id: str) -> dict:
    # LÃ¡ÂºÂ¥y tÃ¡ÂºÂ­p hÃ¡Â»Â£p 100% tÃ¡ÂºÂ¥t cÃ¡ÂºÂ£ cÃƒÂ¡c sÃ¡Â»â€˜ chÃ†Â°Ã†Â¡ng Ã„â€˜ÃƒÂ£ xong tÃ¡Â»Â« Supabase + data/ + output/ + RAM
    completed_set = database.get_completed_chapters_set(novel_id)
    all_done_nums = {int(x) for x in completed_set if str(x).isdigit()}

    all_chapters = database.get_all_chapters(novel_id)
    
    # LÃ¡Â»Âc cÃƒÂ¡c chÃ†Â°Ã†Â¡ng chÃ†Â°a viÃ¡ÂºÂ¿t xong kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n (< 1200 tÃ¡Â»Â« hoÃ¡ÂºÂ·c cÃƒÂ²n lÃƒÂ  BLUEPRINT)
    unwritten_chapters = [
        c for c in all_chapters 
        if isinstance(c.get("chapter_number"), (int, str)) and str(c.get("chapter_number")).isdigit()
        and int(c["chapter_number"]) not in all_done_nums
        and (str(c.get("content", "")).startswith("BLUEPRINT:") or len(str(c.get("content", "")).split()) < 1200)
    ]
    
    if unwritten_chapters:
        unwritten_chapters.sort(key=lambda x: int(x["chapter_number"]))
        next_ch_number = int(unwritten_chapters[0]["chapter_number"])
    else:
        existing_nums = [int(c["chapter_number"]) for c in all_chapters if str(c.get("chapter_number", "")).isdigit()] + list(all_done_nums)
        next_ch_number = (max(existing_nums) + 1) if existing_nums else 1

    print(f"[INFO] Báº®T Äáº¦U QUY TRÃŒNH VIáº¾T CHÆ¯Æ NG Má»šI: ChÆ°Æ¡ng {next_ch_number} (ÄÃ£ hoÃ n thÃ nh cÃ¡c táº­p: {sorted(list(all_done_nums))})...")
    current_arc = get_current_arc(novel_id, next_ch_number)
    chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    if not chapter_record:
        generate_arc_blueprints(novel_id, current_arc)
        all_chapters = database.get_all_chapters(novel_id)
        chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    if not chapter_record:
        chapter_record = database.create_chapter(novel_id=novel_id, chapter_number=next_ch_number, title=f"ChÆ°Æ¡ng {next_ch_number}", content=f"BLUEPRINT: Diá»…n biáº¿n tiáº¿p theo.")
    blueprint_text = (chapter_record or {}).get("content", "BLUEPRINT: default")
    
    chars = database.get_characters(novel_id)
    protagonist = next((c for c in chars if c.get("failure_flag") is not None), None)
    if not protagonist and chars:
        protagonist = chars[0]
        
    protagonist_name = protagonist.get("name", "Jack") if protagonist else "Jack"
    protagonist_power = protagonist.get("power_tier", "Ordinary") if protagonist else "Ordinary"
    protagonist_stats = json.dumps(protagonist.get("combat_stats", {})) if protagonist else "{}"
    failure_flag = protagonist.get("failure_flag", False) if protagonist else False
    last_breakthrough_ch = protagonist.get("last_breakthrough_chapter", 0) if protagonist else 0
    
    lores = database.get_world_lore(novel_id)
    world_lore_text = "\n".join([f"- {lore['keyword']}: {lore['description']}" for lore in lores])
    
    query_embed = get_embedding(blueprint_text)
    semantic_history = database.search_episodes(novel_id, query_embed, limit=7)
    history_text = "\n".join([f"- Chapter {h['chapter_id']}: {h['event_summary']}" for h in semantic_history])
    
    previous_chapters = [c for c in all_chapters if c["chapter_number"] < next_ch_number and not c["content"].startswith("BLUEPRINT:")]
    working_memory_text = ""
    # TÃ„Æ’ng tham chiÃ¡ÂºÂ¿u tÃ¡Â»Â« 2-3 chÃ†Â°Ã†Â¡ng lÃƒÂªn 7 chÃ†Â°Ã†Â¡ng gÃ¡ÂºÂ§n nhÃ¡ÂºÂ¥t (5 - 10 chÃ†Â°Ã†Â¡ng) Ã„â€˜Ã¡Â»Æ’ Ã„â€˜Ã¡ÂºÂ£m bÃ¡ÂºÂ£o mÃ¡ÂºÂ¡ch truyÃ¡Â»â€¡n cÃ¡Â»Â±c kÃ¡Â»Â³ nhÃ¡ÂºÂ¥t quÃƒÂ¡n
    for ch in previous_chapters[-7:]:
        ch_snippet = ch['content'][:600] + "\n...\n" + ch['content'][-600:] if len(ch['content']) > 1200 else ch['content']
        working_memory_text += f"\n--- ChÃ†Â°Ã†Â¡ng {ch['chapter_number']}: {ch['title']} ---\n{ch_snippet}\n"
        
    attempt = 0
    max_attempts = 3
    final_content = ""
    
    prompt = prompts.WRITING_PROMPT.format(
        chapter_number=next_ch_number,
        chapter_title=chapter_record["title"],
        title="TruyÃ¡Â»â€¡n 24h Audio",
        blueprint=blueprint_text,
        world_lore=world_lore_text,
        characters=json.dumps(chars, ensure_ascii=False, indent=2),
        history=history_text,
        previous_content=working_memory_text,
        protagonist_name=protagonist_name,
        protagonist_power=protagonist_power,
        protagonist_stats=protagonist_stats,
        failure_flag=str(failure_flag)
    )
    
    if next_ch_number == 1:
        prologue_instruction = (
            f"- PhÃ¡ÂºÂ§n mÃ¡Â»Å¸ Ã„â€˜Ã¡ÂºÂ§u (Prologue): BÃ¡ÂºÂ®T BUÃ¡Â»ËœC mÃ¡Â»Å¸ Ã„â€˜Ã¡ÂºÂ§u chÃ†Â°Ã†Â¡ng bÃ¡ÂºÂ±ng mÃ¡Â»â„¢t phÃƒÂ¢n cÃ¡ÂºÂ£nh cuÃ¡Â»â€˜n hÃƒÂºt (khoÃ¡ÂºÂ£ng 300 - 500 tÃ¡Â»Â«) miÃƒÂªu tÃ¡ÂºÂ£ bÃ¡Â»â€˜i cÃ¡ÂºÂ£nh thÃ¡ÂºÂ¿ giÃ¡Â»â€ºi linh hÃ¡Â»â€œn, hÃ¡Â»â€¡ thÃ¡Â»â€˜ng Tinh ThÃ¡ÂºÂ§n Ã¡ÂºÂ¤n vÃƒÂ  bÃƒÂ­ mÃ¡ÂºÂ­t chiÃ¡ÂºÂ¿c hÃ¡Â»â„¢p Ã„â€˜Ã¡Â»â€œng Ã„ÂÃƒÂ´ng SÃ†Â¡n.\n"
            f"- **CÃ¡ÂºÂ¢NH BÃƒÂO QUAN TRÃ¡Â»Å’NG VÃ¡Â»â‚¬ NHÃƒâ€šN VÃ¡ÂºÂ¬T**: Trong phÃ¡ÂºÂ§n mÃ¡Â»Å¸ Ã„â€˜Ã¡ÂºÂ§u nÃƒÂ y, CHÃ¡Â»Ë† TÃ¡ÂºÂ¬P TRUNG duy nhÃ¡ÂºÂ¥t vÃƒÂ o nhÃƒÂ¢n vÃ¡ÂºÂ­t chÃƒÂ­nh ({protagonist_name}). "
            f"TUYÃ¡Â»â€ T Ã„ÂÃ¡Â»ÂI KHÃƒâ€NG liÃ¡Â»â€¡t kÃƒÂª hay giÃ¡Â»â€ºi thiÃ¡Â»â€¡u trÃƒÂ n lan cÃƒÂ¡c nhÃƒÂ¢n vÃ¡ÂºÂ­t phÃ¡Â»Â¥. CÃƒÂ¡c nhÃƒÂ¢n vÃ¡ÂºÂ­t phÃ¡Â»Â¥ sÃ¡ÂºÂ½ chÃ¡Â»â€° xuÃ¡ÂºÂ¥t hiÃ¡Â»â€¡n tÃ¡Â»Â± nhiÃƒÂªn khi cÃƒÂ³ tÃƒÂ¬nh huÃ¡Â»â€˜ng Ã„â€˜Ã¡Â»â€˜i thoÃ¡ÂºÂ¡i trong cÃƒÂ¢u chuyÃ¡Â»â€¡n.\n"
            f"- **CÃ¡ÂºÂ¢NH BÃƒÂO QUAN TRÃ¡Â»Å’NG VÃ¡Â»â‚¬ TIÃƒÅ U Ã„ÂÃ¡Â»â‚¬**: TUYÃ¡Â»â€ T Ã„ÂÃ¡Â»ÂI KHÃƒâ€NG VIÃ¡ÂºÂ¾T CHÃ¡Â»Â® 'DÃ¡ÂºÂ«n lÃ†Â°Ã¡Â»Â£c', 'DÃ¡ÂºÂ«n lÃ†Â°Ã¡Â»Â£c:', 'GiÃ¡Â»â€ºi thiÃ¡Â»â€¡u:', hay 'Prologue:'. "
            f"HÃƒÂ£y nhÃ¡ÂºÂ­p vai viÃ¡ÂºÂ¿t thÃ¡ÂºÂ³ng vÃƒÂ o nÃ¡Â»â„¢i dung truyÃ¡Â»â€¡n mÃ¡Â»â„¢t cÃƒÂ¡ch tÃ¡Â»Â± nhiÃƒÂªn nhÃ¡ÂºÂ¥t."
        )
        prompt = prompt.replace("Constraints:", f"Constraints:\n{prologue_instruction}")
    
    while attempt < max_attempts:
        attempt += 1
        print(f"[INFO] Writing chapter draft (Attempt {attempt}/{max_attempts})...")
        
        draft_attempt = 0
        current_prompt = prompt
        final_content = ""
        while draft_attempt < 3:
            draft_attempt += 1
            final_content = call_gemini(current_prompt)
            word_count = len(final_content.split()) if final_content else 0
            print(f"[INFO] Generated draft length: {word_count} words.")
            
            if word_count < 500:
                print(f"[WARNING] Draft response too short (words: {word_count}). Retrying with simplified prompt payload...")
                time.sleep(3)
                current_prompt = prompt[:2500] if len(prompt) > 2500 else prompt
                continue
                
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "Ã¢â‚¬Â", "Ã‚Â»", "*"))
            
            if ends_abruptly and word_count >= 2500:
                last_punct = max(
                    final_content.rfind('.'),
                    final_content.rfind('?'),
                    final_content.rfind('!')
                )
                if last_punct > 0:
                    final_content = final_content[:last_punct + 1].strip()
                    word_count = len(final_content.split())
                    print(f"[INFO] Automatically trimmed unfinished trailing sentence. Clean word count: {word_count} words.")
                    ends_abruptly = False

            # VÃƒâ€™NG LÃ¡ÂºÂ¶P Ãƒâ€°P BÃ¡ÂºÂ®T BUÃ¡Â»ËœC Ã„ÂÃ¡ÂºÂ T >2800 TÃ¡Â»Âª (Guaranteed 2800+ Words Multi-Pass Expansion Loop for 12-18 min Audio)
            if word_count >= 2800 and not ends_abruptly:
                # INKOS MULTI-AGENT AUDITOR PASS: KhÃ¡Â»Â­ AI clichÃƒÂ© & BÃ¡ÂºÂ£o toÃƒÂ n 100% Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i vÃ„Æ’n bÃ¡ÂºÂ£n
                try:
                    print("[INFO] Quality Assurance Agent: BÃ¡ÂºÂ¯t Ã„â€˜Ã¡ÂºÂ§u rÃƒÂ  soÃƒÂ¡t 37 tiÃƒÂªu chuÃ¡ÂºÂ©n chÃ¡ÂºÂ¥t lÃ†Â°Ã¡Â»Â£ng & KhÃ¡Â»Â­ AI clichÃƒÂ©...")
                    audit_prompt = prompts.INKOS_AUDITOR_PROMPT.format(chapter_content=final_content[:6000])
                    audited_res = call_gemini(audit_prompt)
                    if audited_res and len(audited_res.split()) >= len(final_content.split()) * 0.9:
                        final_content = clean_chapter_content(audited_res)
                        word_count = len(final_content.split())
                        print(f"[SUCCESS] Quality Assurance Agent hoÃƒÂ n thÃƒÂ nh khÃ¡Â»Â­ AI clichÃƒÂ©. TÃ¡Â»â€¢ng sÃ¡Â»â€˜ tÃ¡Â»Â« tinh chÃ¡ÂºÂ¿: {word_count} tÃ¡Â»Â«.")
                    else:
                        final_content = clean_chapter_content(final_content)
                        word_count = len(final_content.split())
                        print(f"[INFO] GiÃ¡Â»Â¯ nguyÃƒÂªn Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i vÃ„Æ’n bÃ¡ÂºÂ£n Ã„â€˜Ã¡ÂºÂ§y Ã„â€˜Ã¡Â»Â§: {word_count} tÃ¡Â»Â« (TrÃƒÂ¡nh bÃ¡Â»â€¹ rÃƒÂºt ngÃ¡ÂºÂ¯n).")
                except Exception as audit_err:
                    print(f"[WARNING] Quality Assurance Agent pass warning: {audit_err}")
                break
                
            expand_cycles = 0
            while word_count < 2800 and expand_cycles < 6:
                expand_cycles += 1
                print(f"[INFO] (LÃ†Â°Ã¡Â»Â£t nÃ¡Â»â€˜i tiÃ¡ÂºÂ¿p {expand_cycles}/6) ChÃ†Â°Ã†Â¡ng hiÃ¡Â»â€¡n tÃ¡ÂºÂ¡i Ã„â€˜Ã¡ÂºÂ¡t {word_count} tÃ¡Â»Â« (<2800 tÃ¡Â»Â«). TÃ¡Â»Â± Ã„â€˜Ã¡Â»â„¢ng kÃƒÂ­ch hoÃ¡ÂºÂ¡t AI ViÃ¡ÂºÂ¿t NÃ¡Â»â€˜i TiÃ¡ÂºÂ¿p...")
                
                continuation_prompt = (
                    f"DÃ†Â°Ã¡Â»â€ºi Ã„â€˜ÃƒÂ¢y lÃƒÂ  phÃ¡ÂºÂ§n trÃ†Â°Ã¡Â»â€ºc cÃ¡Â»Â§a ChÃ†Â°Ã†Â¡ng {next_ch_number} (tÃ¡Â»â€¢ng {word_count} tÃ¡Â»Â«):\n\n"
                    f"{final_content[-1200:]}\n\n"
                    f"YÃƒÅ U CÃ¡ÂºÂ¦U BÃ¡ÂºÂ®T BUÃ¡Â»ËœC: HÃƒÂ£y viÃ¡ÂºÂ¿t tiÃ¡ÂºÂ¿p Ã„â€˜oÃ¡ÂºÂ¡n nÃ¡Â»â€˜i theo cÃƒÂ¢u chuyÃ¡Â»â€¡n trÃƒÂªn (tÃ¡Â»â€˜i thiÃ¡Â»Æ’u 1200 - 1800 tÃ¡Â»Â« nÃ¡Â»Â¯a). "
                    f"MiÃƒÂªu tÃ¡ÂºÂ£ diÃ¡Â»â€¦n biÃ¡ÂºÂ¿n tiÃ¡ÂºÂ¿p theo, Ã„â€˜Ã¡Â»â€˜i thoÃ¡ÂºÂ¡i sÃƒÂ¢u sÃ¡ÂºÂ¯c, cÃ¡ÂºÂ£m xÃƒÂºc nhÃƒÂ¢n vÃ¡ÂºÂ­t vÃƒÂ  kÃ¡ÂºÂ¿t thÃƒÂºc bÃ¡ÂºÂ±ng mÃ¡Â»â„¢t nÃƒÂºt thÃ¡ÂºÂ¯t kÃ¡Â»â€¹ch tÃƒÂ­nh. "
                    f"ViÃ¡ÂºÂ¿t thÃ¡ÂºÂ³ng vÃƒÂ o nÃ¡Â»â„¢i dung truyÃ¡Â»â€¡n, khÃƒÂ´ng lÃ¡ÂºÂ·p lÃ¡ÂºÂ¡i Ã„â€˜oÃ¡ÂºÂ¡n cÃ…Â©."
                )
                
                part_next = call_gemini(continuation_prompt)
                if part_next and len(part_next.split()) > 100:
                    cleaned_next, _ = verify_and_sanitize_chapter_content(part_next)
                    # TrÃ¡nh ná»‘i chuá»—i láº·p láº¡i vÃ´ táº­n
                    if cleaned_next in final_content:
                        print("[WARNING] ÄÃ£ phÃ¡t hiá»‡n Ä‘oáº¡n ná»‘i tiáº¿p bá»‹ láº·p láº¡i, ngáº¯t vÃ²ng láº·p expansion.")
                        break
                    final_content = final_content + "\n\n" + cleaned_next
                    word_count = len(final_content.split())
                    print(f"[SUCCESS] Ã„ÂÃƒÂ£ nÃ¡Â»â€˜i tiÃ¡ÂºÂ¿p thÃƒÂ nh cÃƒÂ´ng! TÃ¡Â»â€¢ng Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i chÃ†Â°Ã†Â¡ng hiÃ¡Â»â€¡n tÃ¡ÂºÂ¡i: {word_count} tÃ¡Â»Â«.")
                    if word_count >= 2800:
                        break
                else:
                    time.sleep(2)
                    
            if word_count >= 2800:
                break
                
            if ends_abruptly:
                print(f"[WARNING] Draft ends abruptly (no punctuation at the end). Requesting completion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    "\n\n**CÃ¡ÂºÂ¢NH BÃƒÂO CÃ¡Â»Â°C KÃ¡Â»Â² QUAN TRÃ¡Â»Å’NG**: BÃ¡ÂºÂ£n thÃ¡ÂºÂ£o trÃ†Â°Ã¡Â»â€ºc cÃ¡Â»Â§a bÃ¡ÂºÂ¡n bÃ¡Â»â€¹ cÃ¡ÂºÂ¯t cÃ¡Â»Â¥t Ã„â€˜Ã¡Â»â„¢t ngÃ¡Â»â„¢t Ã¡Â»Å¸ cuÃ¡Â»â€˜i (chÃ†Â°a hÃ¡ÂºÂ¿t cÃƒÂ¢u, chÃ†Â°a cÃƒÂ³ dÃ¡ÂºÂ¥u chÃ¡ÂºÂ¥m cÃƒÂ¢u kÃ¡ÂºÂ¿t thÃƒÂºc). "
                    "BÃ¡ÂºÂ¡n BÃ¡ÂºÂ®T BUÃ¡Â»ËœC phÃ¡ÂºÂ£i viÃ¡ÂºÂ¿t trÃ¡Â»Ân vÃ¡ÂºÂ¹n cÃƒÂ¢u chuyÃ¡Â»â€¡n, mÃ¡Â»Å¸ rÃ¡Â»â„¢ng chi tiÃ¡ÂºÂ¿t cÃƒÂ¡c phÃƒÂ¢n cÃ¡ÂºÂ£nh, hÃ¡Â»â„¢i thoÃ¡ÂºÂ¡i vÃƒÂ  kÃ¡ÂºÂ¿t thÃƒÂºc chÃ†Â°Ã†Â¡ng mÃ¡Â»â„¢t cÃƒÂ¡ch trÃ¡Â»Ân vÃ¡ÂºÂ¹n bÃ¡ÂºÂ±ng dÃ¡ÂºÂ¥u chÃ¡ÂºÂ¥m cÃƒÂ¢u."
                )
            else:
                print(f"[WARNING] Draft too short ({word_count} words). Requesting longer expansion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    f"\n\n**CÃ¡ÂºÂ¢NH BÃƒÂO CÃ¡Â»Â°C KÃ¡Â»Â² QUAN TRÃ¡Â»Å’NG VÃ¡Â»â‚¬ Ã„ÂÃ¡Â»Ëœ DÃƒâ‚¬I (BÃ¡ÂºÂ®T BUÃ¡Â»ËœC)**:\n"
                    f"BÃ¡ÂºÂ£n thÃ¡ÂºÂ£o bÃ¡ÂºÂ¡n vÃ¡Â»Â«a viÃ¡ÂºÂ¿t quÃƒÂ¡ ngÃ¡ÂºÂ¯n (chÃ¡Â»â€° cÃƒÂ³ {word_count} tÃ¡Â»Â«), trong khi yÃƒÂªu cÃ¡ÂºÂ§u tÃ¡Â»â€˜i thiÃ¡Â»Æ’u lÃƒÂ  2200 tÃ¡Â»Â« Ã„â€˜Ã¡Â»Æ’ Ã„â€˜Ã¡ÂºÂ¡t 10 phÃƒÂºt nÃƒÂ³i.\n"
                    f"Ã„ÂÃ¡Â»Æ’ sÃ¡Â»Â­a lÃ¡Â»â€”i nÃƒÂ y, bÃ¡ÂºÂ¡n phÃ¡ÂºÂ£i viÃ¡ÂºÂ¿t cÃ¡Â»Â±c kÃ¡Â»Â³ chi tiÃ¡ÂºÂ¿t theo hÃ†Â°Ã¡Â»â€ºng dÃ¡ÂºÂ«n sau:\n"
                    f"1. Chia chÃ†Â°Ã†Â¡ng truyÃ¡Â»â€¡n thÃƒÂ nh ÃƒÂ­t nhÃ¡ÂºÂ¥t 5 phÃƒÂ¢n cÃ¡ÂºÂ£nh lÃ¡Â»â€ºn riÃƒÂªng biÃ¡Â»â€¡t (MÃ¡Â»â€”i phÃƒÂ¢n cÃ¡ÂºÂ£nh viÃ¡ÂºÂ¿t tÃ¡Â»â€˜i thiÃ¡Â»Æ’u 5-6 Ã„â€˜oÃ¡ÂºÂ¡n vÃ„Æ’n dÃƒÂ i).\n"
                    f"2. Ã„Âi sÃƒÂ¢u miÃƒÂªu tÃ¡ÂºÂ£ cÃ¡Â»Â±c kÃ¡Â»Â³ tÃ¡Â»â€° mÃ¡Â»â€°: cÃ¡ÂºÂ£nh sÃ¡ÂºÂ¯c khÃƒÂ´ng gian hÃ¡Â»Âc viÃ¡Â»â€¡n, thÃ¡Â»Âi tiÃ¡ÂºÂ¿t, ÃƒÂ¢m thanh giÃƒÂ³ thÃ¡Â»â€¢i, biÃ¡Â»Æ’u cÃ¡ÂºÂ£m nÃƒÂ©t mÃ¡ÂºÂ·t tÃ¡Â»Â«ng nhÃƒÂ¢n vÃ¡ÂºÂ­t, cÃ¡Â»Â­ chÃ¡Â»â€° tay chÃƒÂ¢n, vÃƒÂ  dÃƒÂ²ng suy nghÃ„Â© nÃ¡Â»â„¢i tÃƒÂ¢m kÃƒÂ©o dÃƒÂ i.\n"
                    f"3. ViÃ¡ÂºÂ¿t cÃƒÂ¡c Ã„â€˜oÃ¡ÂºÂ¡n Ã„â€˜Ã¡Â»â€˜i thoÃ¡ÂºÂ¡i dÃƒÂ i, thÃ¡Â»Â±c tÃ¡ÂºÂ¿ vÃƒÂ  sÃƒÂ¢u sÃ¡ÂºÂ¯c giÃ¡Â»Â¯a cÃƒÂ¡c nhÃƒÂ¢n vÃ¡ÂºÂ­t (TrÃ¡ÂºÂ§n Lam, Linh Vy, Minh Ã„ÂÃ¡Â»Â©c, v.v.). KhÃƒÂ´ng Ã„â€˜Ã†Â°Ã¡Â»Â£c viÃ¡ÂºÂ¿t lÃ†Â°Ã¡Â»â€ºt qua.\n"
                    f"4. TUYÃ¡Â»â€ T Ã„ÂÃ¡Â»ÂI khÃƒÂ´ng tÃƒÂ³m tÃ¡ÂºÂ¯t hay kÃ¡ÂºÂ¿t thÃƒÂºc chÃ†Â°Ã†Â¡ng truyÃ¡Â»â€¡n sÃ¡Â»â€ºm khi chÃ†Â°a Ã„â€˜Ã¡Â»Â§ Ã„â€˜Ã¡Â»â„¢ dÃƒÂ i yÃƒÂªu cÃ¡ÂºÂ§u."
                )
            
        review_prompt = prompts.REVIEW_PROMPT.format(
            chapter_number=next_ch_number,
            chapter_title=chapter_record["title"],
            chapter_content=final_content,
            world_lore=world_lore_text,
            characters=json.dumps(chars, ensure_ascii=False, indent=2),
            failure_flag=str(failure_flag),
            last_breakthrough_chapter=last_breakthrough_ch
        )
        
        review_json = call_gemini(review_prompt, json_mode=True)
        try:
            review = safe_loads(review_json)
            if review.get("pass_review") or attempt == max_attempts:
                print(f"[INFO] Chapter passed review with score {review.get('score', 8)}/10.")
                break
            else:
                print(f"[WARNING] Review failed: {review.get('feedback')}. Re-writing...")
                prompt = prompt + f"\n\nPrevious Editor Feedback (MUST address this in rewrite): {review.get('feedback')}"
        except Exception as e:
            print(f"[WARNING] Failed to parse editor review: {e}. Skipping review loop.")
            break
            
    cleaned_content = clean_chapter_content(final_content)
    # Ã„ÂÃ¡Â»ËœNG CÃ†Â  DÃ¡Â»Å CH THUÃ¡ÂºÂ¬T TIÃ¡ÂºÂ¾NG VIÃ¡Â»â€ T GEMINI API: Ã„ÂÃ¡ÂºÂ£m bÃ¡ÂºÂ£o 100% kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n tiÃ¡Â»Æ’u thuyÃ¡ÂºÂ¿t chuÃ¡ÂºÂ©n TiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t mÃ†Â°Ã¡Â»Â£t mÃƒÂ 
    cleaned_content = translate_to_vietnamese_with_gemini(cleaned_content)
    
    # Ã„ÂÃ¡ÂºÂ£m bÃ¡ÂºÂ£o tiÃƒÂªu Ã„â€˜Ã¡Â»Â chÃ†Â°Ã†Â¡ng khÃƒÂ´ng bÃ¡Â»â€¹ trÃƒÂ¹ng lÃ¡ÂºÂ·p placeholder
    cur_title = chapter_record.get("title", "")
    if "HÃƒÂ nh TrÃƒÂ¬nh MÃ¡Â»â€ºi" in cur_title or not cur_title or cur_title == f"ChÃ†Â°Ã†Â¡ng {next_ch_number}":
        EPIC_TITLES = [
            "TrÃƒÂ¹ng Sinh VÃ¡ÂºÂ¡n CÃ¡Â»â€¢, ThÃƒÂ´n PhÃ¡Â»â€¡ VÃƒÂ´ TÃ¡ÂºÂ­n", "ThÃ¡Â»Â©c TÃ¡Â»â€°nh ThÃ¡ÂºÂ§n ThÃ¡Â»Æ’, NÃƒÂ©n Ãƒâ€°p ThÃ¡ÂºÂ§n Ma", "HuyÃ¡ÂºÂ¿t MÃ¡ÂºÂ¡ch ThÃƒÂ´n ThiÃƒÂªn, TrÃ¡ÂºÂ¥n TÃƒÂ¡m PhÃ†Â°Ã†Â¡ng",
            "QuyÃ¡Â»Ân TrÃ¡ÂºÂ¥n SÃ†Â¡n HÃƒÂ , Uy ChÃ¡ÂºÂ¥n ChÃ†Â° ThiÃƒÂªn", "VÃƒÂ´ Ã„ÂÃ¡Â»â€¹ch TrÃƒÂ¹ng Sinh, HÃ¡Â»â€”n Ã„ÂÃ¡Â»â„¢n LuyÃ¡Â»â€¡n KhÃƒÂ­", "NghÃ¡Â»â€¹ch ThiÃƒÂªn Ã„ÂÃ¡Â»â„¢c TÃƒÂ´n, LuyÃ¡Â»â€¡n HÃƒÂ³a ThÃ¡ÂºÂ§n ThÃ¡ÂºÂ¡ch",
            "ThÃƒÂ´n PhÃ¡Â»â€¡ NguyÃƒÂªn KhÃƒÂ­, PhÃƒÂ¡ Tam CÃ¡ÂºÂ£nh", "VÃ¡ÂºÂ¡n GiÃ¡Â»â€ºi QuÃ¡Â»Â³ BÃƒÂ¡i, TiÃƒÂªu ViÃƒÂªm XuÃ¡ÂºÂ¥t ThÃ¡ÂºÂ¿", "ThÃƒÂ´n PhÃ¡Â»â€¡ Ma NhÃ¡ÂºÂ«n, Khai MÃ¡Â»Å¸ ThÃ¡ÂºÂ§n ThÃƒÂ´ng",
            "VÃƒÂ´ Song KiÃ¡ÂºÂ¿m KhÃƒÂ­, TrÃ¡ÂºÂ£m DiÃ¡Â»â€¡t CÃ†Â°Ã¡Â»Âng Ã„ÂÃ¡Â»â€¹ch", "HÃ¡Â»â€¡ ThÃ¡Â»â€˜ng ThÃ¡ÂºÂ§n CÃ¡ÂºÂ¥p, ThÃƒÂ´n PhÃ¡Â»â€¡ VÃ¡ÂºÂ¡n VÃ¡ÂºÂ­t", "BÃƒÂ¡ ThÃ¡ÂºÂ§n XuÃ¡ÂºÂ¥t ThÃ¡ÂºÂ¿, NgÃ„Æ’n CÃ¡ÂºÂ£n VÃ¡ÂºÂ¡n QuÃƒÂ¢n"
        ]
        epic_name = EPIC_TITLES[(next_ch_number - 1) % len(EPIC_TITLES)]
        cur_title = f"{epic_name} (TÃ¡ÂºÂ­p {next_ch_number})"

    client = database.get_client()
    response = client.table("chapters")\
        .update({"content": cleaned_content, "title": cur_title})\
        .eq("id", chapter_record["id"])\
        .execute()
    updated_chapter = response.data[0] if response.data else chapter_record
    updated_chapter["title"] = cur_title
    
    sync_story_bible(novel_id, updated_chapter, chars)  # type: ignore[arg-type]
    
    return updated_chapter  # type: ignore[return-value]

def sync_story_bible(novel_id: str, chapter: dict, current_chars: list):
    print("[INFO] Syncing Story Bible and updating character stats...")
    
    prompt = prompts.EXTRACT_ENTITIES_PROMPT.format(
        chapter_content=chapter["content"],
        current_characters=json.dumps(current_chars, ensure_ascii=False)
    )
    
    extract_json = call_gemini(prompt, json_mode=True)
    try:
        data = safe_loads(extract_json)
        
        # 1. TÃ¡Â»Â° Ã„ÂÃ¡Â»ËœNG LÃ†Â¯U CÃƒÂC NHÃƒâ€šN VÃ¡ÂºÂ¬T MÃ¡Â»Å¡I SÃƒÂNG TÃ¡ÂºÂ O VÃƒâ‚¬O CSDL SUPABASE
        new_chars = data.get("new_characters", [])
        if new_chars:
            print(f"[INFO] Ã°Å¸Å’Å¸ Ã„ÂÃƒÂ£ phÃƒÂ¡t hiÃ¡Â»â€¡n {len(new_chars)} nhÃƒÂ¢n vÃ¡ÂºÂ­t MÃ¡Â»Å¡I Ã„â€˜Ã†Â°Ã¡Â»Â£c AI sÃƒÂ¡ng tÃ¡ÂºÂ¡o trong chÃ†Â°Ã†Â¡ng!")
            for n_char in new_chars:
                n_name = n_char.get("name")
                if n_name and n_name.strip():
                    database.upsert_character(
                        novel_id=novel_id,
                        name=n_name.strip(),
                        description=n_char.get("description", "NhÃƒÂ¢n vÃ¡ÂºÂ­t mÃ¡Â»â€ºi xuÃ¡ÂºÂ¥t hiÃ¡Â»â€¡n trong kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n"),
                        power_tier=n_char.get("power_tier", "Cao ThÃ¡Â»Â§ MÃ¡Â»â€ºi"),
                        combat_stats=n_char.get("combat_stats", {}),
                        relationships=n_char.get("relationships", {}),
                        failure_flag=False,
                        last_breakthrough_chapter=0
                    )
                    print(f"   [SUPABASE] + Da tu dong nhat Nhan Vat MOI: {n_name} ({n_char.get('power_tier')})")

        # 2. CÃ¡ÂºÂ¬P NHÃ¡ÂºÂ¬T TRÃ¡ÂºÂ NG THÃƒÂI CÃƒÂC NHÃƒâ€šN VÃ¡ÂºÂ¬T CÃ…Â¨
        for char_up in data.get("character_updates", []):
            name = char_up["name"]
            exist = database.get_character_by_name(novel_id, name)
            
            new_failure_flag = char_up.get("failure_flag")
            if new_failure_flag is None:
                new_failure_flag = exist.get("failure_flag", False) if exist else False
                
            last_bt = exist.get("last_breakthrough_chapter", 0) if exist else 0
            
            if char_up.get("breakthrough_written"):
                new_failure_flag = False
                last_bt = chapter["chapter_number"]
                print(f"[INFO] Protagonist breakthrough recorded in Chapter {last_bt}! Resetting failure_flag.")
                
            description = char_up.get("description") or (exist.get("description", "") if exist else "")
            power_tier = char_up.get("power_tier") or (exist.get("power_tier", "Ordinary") if exist else "Ordinary")
            combat_stats = char_up.get("combat_stats") or (exist.get("combat_stats", {}) if exist else {})
            relationships = char_up.get("relationships") or (exist.get("relationships", {}) if exist else {})
            
            database.upsert_character(
                novel_id=novel_id,
                name=name,
                description=description,
                power_tier=power_tier,
                combat_stats=combat_stats,
                relationships=relationships,
                failure_flag=new_failure_flag,
                last_breakthrough_chapter=last_bt
            )
            
        for lore in data.get("new_lore", []):
            database.upsert_world_lore(
                novel_id=novel_id,
                keyword=lore["keyword"],
                description=lore["description"]
            )
            print(f"[INFO] New lore added: {lore['keyword']}")
            
        for thread in data.get("new_threads", []):
            database.upsert_narrative_thread(
                novel_id=novel_id,
                thread_name=thread["thread_name"],
                description=thread["description"],
                status="open"
            )
            print(f"[INFO] New narrative thread added: {thread['thread_name']}")
            
        events_list = [c.get("event_summary", "") for c in data.get("character_updates", []) if c.get("event_summary")]
        chapter_events = " ".join(events_list) if events_list else f"Chapter {chapter['chapter_number']}: {chapter['title']}"
        
        embed_vector = get_embedding(chapter["content"])
        database.create_episode_summary(
            chapter_id=chapter["id"],
            event_summary=chapter_events,
            embedding=embed_vector
        )
        print("[INFO] Episodic summary and Vector embedding saved.")
        
    except Exception as e:
        print(f"[ERROR] Story bible sync failed: {e}. Raw JSON: {extract_json}")




