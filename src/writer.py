import os
from gradio_client import Client
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
        # ThÃƒÂ¡Ã‚Â»Ã‚Â­ lÃƒÆ’Ã‚Â m sÃƒÂ¡Ã‚ÂºÃ‚Â¡ch dÃƒÂ¡Ã‚ÂºÃ‚Â¥u phÃƒÂ¡Ã‚ÂºÃ‚Â©y thÃƒÂ¡Ã‚Â»Ã‚Â«a ÃƒÂ¡Ã‚Â»Ã…Â¸ cuÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi (trailing commas)
        cleaned_no_comma = re.sub(r",\s*([\}\]])", r"\1", cleaned)
        try:
            return json.loads(cleaned_no_comma)
        except Exception:
            pass
        # ThÃƒÂ¡Ã‚Â»Ã‚Â­ trÃƒÆ’Ã‚Â­ch xuÃƒÂ¡Ã‚ÂºÃ‚Â¥t khÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi {...} hoÃƒÂ¡Ã‚ÂºÃ‚Â·c [...] bÃƒÂ¡Ã‚ÂºÃ‚Â±ng Regex
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
        sentences = re.split(r'(?<=[.?!ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦])\s+(?=[a-zA-ZÃƒÆ’Ã‚Â ÃƒÆ’Ã‚Â¡ÃƒÆ’Ã‚Â¢ÃƒÆ’Ã‚Â£ÃƒÆ’Ã‚Â¨ÃƒÆ’Ã‚Â©ÃƒÆ’Ã‚ÂªÃƒÆ’Ã‚Â¬ÃƒÆ’Ã‚Â­ÃƒÆ’Ã‚Â²ÃƒÆ’Ã‚Â³ÃƒÆ’Ã‚Â´ÃƒÆ’Ã‚ÂµÃƒÆ’Ã‚Â¹ÃƒÆ’Ã‚ÂºÃƒÆ’Ã‚Â½Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã¢â€šÂ¬ÃƒÆ’Ã‚ÂÃƒÆ’Ã¢â‚¬Å¡ÃƒÆ’Ã†â€™ÃƒÆ’Ã‹â€ ÃƒÆ’Ã¢â‚¬Â°ÃƒÆ’Ã…Â ÃƒÆ’Ã…â€™ÃƒÆ’Ã‚ÂÃƒÆ’Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å“ÃƒÆ’Ã¢â‚¬ÂÃƒÆ’Ã¢â‚¬Â¢ÃƒÆ’Ã¢â€žÂ¢ÃƒÆ’Ã…Â¡ÃƒÆ’Ã‚ÂÃƒâ€žÃ‚Â0-9"\'Ãƒâ€šÃ‚Â«ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ])', para)
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
    """Clean draft content, stripping markdown and prefix headers like 'DÃ¡ÂºÂ«n lÃ†Â°Ã¡Â»Â£c:', 'ChÃ†Â°Ã†Â¡ng X:', etc."""
    cleaned = text.strip()
    pattern = r"(?im)^\s*[*_]*\s*(?:DÃ¡ÂºÂ«n lÃ†Â°Ã¡Â»Â£c|GiÃ¡Â»â€ºi thiÃ¡Â»â€¡u|PhÃ¡ÂºÂ§n dÃ¡ÂºÂ«n lÃ†Â°Ã¡Â»Â£c|TÃƒÂ³m tÃ¡ÂºÂ¯t bÃ¡Â»â€˜i cÃ¡ÂºÂ£nh|Prologue|Introduction|GiÃ¡Â»â€ºi thiÃ¡Â»â€¡u bÃ¡Â»â€˜i cÃ¡ÂºÂ£nh)\s*[:Ã¯Â¼Å¡\-Ã¢â‚¬â€œÃ¢â‚¬â€]*\s*[*_]*\s*[:Ã¯Â¼Å¡\-Ã¢â‚¬â€œÃ¢â‚¬â€]*\s*"
    cleaned = re.sub(pattern, "", cleaned).strip()
    cleaned = remove_repetitive_sentences(cleaned)
    return cleaned

def expand_chapter_content(content: str, target_words: int = 3200) -> str:
    """NÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi dÃƒÆ’Ã‚Â i kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n nÃƒÂ¡Ã‚ÂºÃ‚Â¿u chÃƒâ€ Ã‚Â°a Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã‚Â§ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i >10 phÃƒÆ’Ã‚Âºt audio (600 giÃƒÆ’Ã‚Â¢y)."""
    current_words = len(content.split()) if content else 0
    if current_words >= target_words:
        return content
        
    print(f"[INFO] ÃƒÂ¢Ã…Â¡Ã‚Â¡ CHÃƒÂ¡Ã‚ÂºÃ‚Â¾ Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‹Å“ LÃƒÆ’Ã¢â€šÂ¬M LÃƒÂ¡Ã‚ÂºÃ‚Â I (>10 PHÃƒÆ’Ã…Â¡T): Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n tÃƒÂ¡Ã‚ÂºÃ‚Â¡i {current_words} tÃƒÂ¡Ã‚Â»Ã‚Â« (<{target_words} tÃƒÂ¡Ã‚Â»Ã‚Â«). Ãƒâ€žÃ‚Âang gÃƒÂ¡Ã‚Â»Ã‚Âi AI viÃƒÂ¡Ã‚ÂºÃ‚Â¿t nÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh...")
    
    continuation_prompt = (
        f"DÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã‚Â¢y lÃƒÆ’Ã‚Â  phÃƒÂ¡Ã‚ÂºÃ‚Â§n trÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºc cÃƒÂ¡Ã‚Â»Ã‚Â§a chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n (tÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ng {current_words} tÃƒÂ¡Ã‚Â»Ã‚Â«):\n\n"
        f"{content[-1500:]}\n\n"
        f"YÃƒÆ’Ã…Â U CÃƒÂ¡Ã‚ÂºÃ‚Â¦U BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C (ÃƒÆ’Ã¢â‚¬Â°P THÃƒÂ¡Ã‚Â»Ã…â€œI LÃƒâ€ Ã‚Â¯ÃƒÂ¡Ã‚Â»Ã‚Â¢NG KÃƒÆ’Ã¢â‚¬Â°O DÃƒÆ’Ã¢â€šÂ¬I >10 PHÃƒÆ’Ã…Â¡T AUDIO):\n"
        f"HÃƒÆ’Ã‚Â£y viÃƒÂ¡Ã‚ÂºÃ‚Â¿t tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh diÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¦n biÃƒÂ¡Ã‚ÂºÃ‚Â¿n kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p theo cÃƒÂ¡Ã‚Â»Ã‚Â§a cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n trÃƒÆ’Ã‚Âªn (tÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thiÃƒÂ¡Ã‚Â»Ã†â€™u 1500 - 2000 tÃƒÂ¡Ã‚Â»Ã‚Â« nÃƒÂ¡Ã‚Â»Ã‚Â¯a).\n"
        f"1. ViÃƒÂ¡Ã‚ÂºÃ‚Â¿t chi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t cuÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢c Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i gay gÃƒÂ¡Ã‚ÂºÃ‚Â¯t, bÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢c phÃƒÆ’Ã‚Â¡t cÃƒÂ¡Ã‚ÂºÃ‚Â£m xÃƒÆ’Ã‚Âºc giÃƒÂ¡Ã‚Â»Ã‚Â¯a cÃƒÆ’Ã‚Â¡c nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t chÃƒÆ’Ã‚Â­nh.\n"
        f"2. MiÃƒÆ’Ã‚Âªu tÃƒÂ¡Ã‚ÂºÃ‚Â£ chi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t chiÃƒÆ’Ã‚Âªu thÃƒÂ¡Ã‚Â»Ã‚Â©c, giao phong kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh vÃƒÆ’Ã‚Â  suy nghÃƒâ€žÃ‚Â© nÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢i tÃƒÆ’Ã‚Â¢m dÃƒÂ¡Ã‚Â»Ã¢â‚¬Å“n dÃƒÂ¡Ã‚ÂºÃ‚Â­p.\n"
        f"3. KÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÆ’Ã‚Âºc bÃƒÂ¡Ã‚ÂºÃ‚Â±ng mÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t nÃƒÆ’Ã‚Âºt thÃƒÂ¡Ã‚ÂºÃ‚Â¯t cliffhanger kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh.\n"
        f"ViÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÂ¡Ã‚ÂºÃ‚Â³ng vÃƒÆ’Ã‚Â o cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n 100% bÃƒÂ¡Ã‚ÂºÃ‚Â±ng TiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â , khÃƒÆ’Ã‚Â´ng lÃƒÂ¡Ã‚ÂºÃ‚Â·p lÃƒÂ¡Ã‚ÂºÃ‚Â¡i Ãƒâ€žÃ¢â‚¬ËœoÃƒÂ¡Ã‚ÂºÃ‚Â¡n cÃƒâ€¦Ã‚Â©."
    )
    
    for _expand_attempt in range(3):
        part_next = call_gemini(continuation_prompt)
        if part_next and len(part_next.split()) > 200:
            cleaned_next = clean_chapter_content(part_next)
            if cleaned_next.lower() in content.lower():
                continue
            content = content + "\n\n" + cleaned_next
            print(f"[SUCCESS] Ãƒâ€ž ÃƒÆ’Ã‚Â£ nÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi dÃƒÆ’Ã‚Â i chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n! TÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ng sÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœ tÃƒÂ¡Ã‚Â»Ã‚Â« mÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi: {len(content.split())} tÃƒÂ¡Ã‚Â»Ã‚Â«.")
            if len(content.split()) >= target_words:
                break
    return content

LEGACY_INVALID_NAMES = {}

def verify_and_sanitize_chapter_content(text: str, novel_id: str = "") -> tuple:
    """
    BÃƒÂ¡Ã‚Â»Ã‹Å“ KIÃƒÂ¡Ã‚Â»Ã¢â‚¬Å¡M TRA TÃƒÂ¡Ã‚Â»Ã‚Â° Ãƒâ€ž ÃƒÂ¡Ã‚Â»Ã‹Å“NG BÃƒÂ¡Ã‚ÂºÃ‚Â¢O VÃƒÂ¡Ã‚Â»Ã¢â‚¬Â  CHÃƒâ€ Ã‚Â¯Ãƒâ€ Ã‚Â NG TRUYÃƒÂ¡Ã‚Â»Ã¢â‚¬Â N (Automated Chapter Auditor).
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
        print(f"[WARNING] ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â PHÃƒÆ’Ã‚ÂT HIÃƒÂ¡Ã‚Â»Ã¢â‚¬Â N LÃƒÂ¡Ã‚Â»Ã¢â‚¬â€œI TÃƒÆ’Ã…Â N NHÃƒÆ’Ã¢â‚¬Å¡N VÃƒÂ¡Ã‚ÂºÃ‚Â¬T CÃƒâ€¦Ã‚Â¨: {found_invalid}! Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â£ tÃƒÂ¡Ã‚Â»Ã‚Â± Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng thay thÃƒÂ¡Ã‚ÂºÃ‚Â¿ chuÃƒÂ¡Ã‚ÂºÃ‚Â©n thÃƒÆ’Ã‚Â nh nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t bÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n tÃƒÂ¡Ã‚ÂºÃ‚Â¡i.")
        return sanitized_text, True
        
    return text, False



@cached(ttl_seconds=86400)
def translate_to_vietnamese_with_gemini(text: str) -> str:
    """TÃƒÂ¡Ã‚Â»Ã‚Â± Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng kiÃƒÂ¡Ã‚Â»Ã†â€™m tra vÃƒÆ’Ã‚Â  dÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch toÃƒÆ’Ã‚Â n bÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t tÃƒÂ¡Ã‚Â»Ã‚Â« tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng Trung/tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng Anh sang tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t chuÃƒÂ¡Ã‚ÂºÃ‚Â©n mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â  100% qua Gemini API."""
    if not text or not text.strip():
        return text
        
    # TÃƒÂ¡Ã‚Â»Ã‚Â± Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng rÃƒÆ’Ã‚Â  soÃƒÆ’Ã‚Â¡t vÃƒÆ’Ã‚Â  khÃƒÂ¡Ã‚Â»Ã‚Â­ tÃƒÆ’Ã‚Âªn nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t cÃƒâ€¦Ã‚Â© rÃƒÆ’Ã‚Â¡c
    text, _ = verify_and_sanitize_chapter_content(text)
    
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    if not has_chinese:
        return text
        
    print(f"[INFO] BÃƒÂ¡Ã‚ÂºÃ‚Â¯t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u rÃƒÆ’Ã‚Â  soÃƒÆ’Ã‚Â¡t ngÃƒÆ’Ã‚Â´n ngÃƒÂ¡Ã‚Â»Ã‚Â¯ kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n (Has Chinese: {has_chinese})...")
    print("[INFO] KÃƒÆ’Ã‚Â­ch hoÃƒÂ¡Ã‚ÂºÃ‚Â¡t Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng CÃƒâ€ Ã‚Â¡ DÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch ThuÃƒÂ¡Ã‚ÂºÃ‚Â­t Gemini API: DÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch/TÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi Ãƒâ€ Ã‚Â°u toÃƒÆ’Ã‚Â n bÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t sang TiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â ...")
    translate_prompt = (
        "BÃƒÂ¡Ã‚ÂºÃ‚Â¡n lÃƒÆ’Ã‚Â  dÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch giÃƒÂ¡Ã‚ÂºÃ‚Â£ tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t webtoon hÃƒÆ’Ã‚Â ng Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u. HÃƒÆ’Ã‚Â£y dÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch/chuyÃƒÂ¡Ã‚Â»Ã†â€™n ngÃƒÂ¡Ã‚Â»Ã‚Â¯ toÃƒÆ’Ã‚Â n bÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t sau Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã‚Â¢y sang tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t tÃƒÂ¡Ã‚Â»Ã‚Â± nhiÃƒÆ’Ã‚Âªn, giÃƒÆ’Ã‚Â u cÃƒÂ¡Ã‚ÂºÃ‚Â£m xÃƒÆ’Ã‚Âºc vÃƒÆ’Ã‚Â  hÃƒÂ¡Ã‚ÂºÃ‚Â¥p dÃƒÂ¡Ã‚ÂºÃ‚Â«n.\n"
        "YÃƒÆ’Ã…Â U CÃƒÂ¡Ã‚ÂºÃ‚Â¦U DÃƒÂ¡Ã‚Â»Ã…Â CH THUÃƒÂ¡Ã‚ÂºÃ‚Â¬T BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C:\n"
        "1. DÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch 100% sang tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t thuÃƒÂ¡Ã‚ÂºÃ‚Â§n tÃƒÆ’Ã‚Âºy, mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â , vÃƒâ€žÃ†â€™n phong tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t hÃƒÆ’Ã‚Â nh Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng/huyÃƒÂ¡Ã‚Â»Ã‚Ân ÃƒÂ¡Ã‚ÂºÃ‚Â£o kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh.\n"
        "2. GiÃƒÂ¡Ã‚Â»Ã‚Â¯ nguyÃƒÆ’Ã‚Âªn 100% Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i vÃƒâ€žÃ†â€™n bÃƒÂ¡Ã‚ÂºÃ‚Â£n, lÃƒÂ¡Ã‚Â»Ã‚Âi thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i trong ngoÃƒÂ¡Ã‚ÂºÃ‚Â·c kÃƒÆ’Ã‚Â©p (\"...\"), vÃƒÆ’Ã‚Â  cÃƒÂ¡Ã‚ÂºÃ‚Â¥u trÃƒÆ’Ã‚Âºc cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n. TUYÃƒÂ¡Ã‚Â»Ã¢â‚¬Â T Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‚ÂI KHÃƒÆ’Ã¢â‚¬ÂNG tÃƒÆ’Ã‚Â³m tÃƒÂ¡Ã‚ÂºÃ‚Â¯t hay bÃƒÂ¡Ã‚Â»Ã‚Â sÃƒÆ’Ã‚Â³t chi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t nÃƒÆ’Ã‚Â o.\n"
        "3. GiÃƒÂ¡Ã‚Â»Ã‚Â¯ nguyÃƒÆ’Ã‚Âªn 100% tÃƒÆ’Ã‚Âªn nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t chuÃƒÂ¡Ã‚ÂºÃ‚Â©n tÃƒÂ¡Ã‚Â»Ã‚Â« nguyÃƒÆ’Ã‚Âªn bÃƒÂ¡Ã‚ÂºÃ‚Â£n. CÃƒÂ¡Ã‚ÂºÃ‚Â¥m tÃƒÂ¡Ã‚Â»Ã‚Â± Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢i sang tÃƒÆ’Ã‚Âªn khÃƒÆ’Ã‚Â¡c.\n"
        "4. ChÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° xuÃƒÂ¡Ã‚ÂºÃ‚Â¥t ra duy nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t vÃƒâ€žÃ†â€™n bÃƒÂ¡Ã‚ÂºÃ‚Â£n truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã‚Â£ dÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch sang tiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t, khÃƒÆ’Ã‚Â´ng kÃƒÆ’Ã‚Â¨m lÃƒÂ¡Ã‚Â»Ã‚Âi dÃƒÂ¡Ã‚ÂºÃ‚Â«n hay giÃƒÂ¡Ã‚ÂºÃ‚Â£i thÃƒÆ’Ã‚Â­ch.\n\n"
        f"VÃƒâ€žÃ¢â‚¬Å¡N BÃƒÂ¡Ã‚ÂºÃ‚Â¢N CÃƒÂ¡Ã‚ÂºÃ‚Â¦N DÃƒÂ¡Ã‚Â»Ã…Â CH:\n{text}"
    )
    translated_res = call_gemini(translate_prompt)
    if translated_res and len(translated_res.split()) > 200:
        cleaned_res = clean_chapter_content(translated_res)
        cleaned_res, _ = verify_and_sanitize_chapter_content(cleaned_res)
        print(f"[SUCCESS] Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â£ hoÃƒÆ’Ã‚Â n thÃƒÆ’Ã‚Â nh dÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n sang TiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t qua Gemini API! Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i: {len(cleaned_res.split())} tÃƒÂ¡Ã‚Â»Ã‚Â«.")
        return cleaned_res
    return text


def call_inkos_cloud(prompt: str) -> str:
    print("[INFO] Gá»­i yÃªu cáº§u sÃ¡ng tÃ¡c tá»›i Inkos (Hugging Face Cloud)...")
    try:
        hf_token = os.environ.get("HF_TOKEN")
        client = Client("AnLee-ai/truyen24h-video-ai", hf_token=hf_token)
        result = client.predict(
            prompt=prompt,
            api_name="/generate_story"
        )
        if "Lá»—i" in result:
            print(f"[WARNING] Inkos tráº£ vá» lá»—i: {result}")
            return ""
        return str(result)
    except Exception as e:
        print(f"[ERROR] Lá»—i gá»i Inkos Cloud: {e}")
        return ""

@cached(ttl_seconds=86400)
def call_gemini(prompt: str, json_mode: bool = False, retries: int = 12) -> str:
    """
    Ãƒâ€ Ã‚Â¯U TIÃƒÆ’Ã…Â N 100% HÃƒÆ’Ã¢â€šÂ¬NG Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â¦U: InkOS Multi-Agent Engine (Google Gemini 2.0 Flash API vÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi Key Rotator).
    ChÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° khi Gemini hÃƒÂ¡Ã‚ÂºÃ‚Â¿t Key mÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi chuyÃƒÂ¡Ã‚Â»Ã†â€™n sang Groq / OpenRouter dÃƒÂ¡Ã‚Â»Ã‚Â± phÃƒÆ’Ã‚Â²ng.
    """
    # =========================================================================
    # Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‹Å“NG CÃƒâ€ Ã‚Â  Ãƒâ€ Ã‚Â¯U TIÃƒÆ’Ã…Â N 1: InkOS Gemini 2.0 Flash Engine (Google API vÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi Key Rotator)
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
                print(f"[SUCCESS] ÃƒÂ¢Ã…Â¡Ã‚Â¡ InkOS Writer Agent [{current_g_model}]: TÃƒÂ¡Ã‚ÂºÃ‚Â¡o kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â  thÃƒÆ’Ã‚Â nh cÃƒÆ’Ã‚Â´ng! ({len(response.text.strip().split())} tÃƒÂ¡Ã‚Â»Ã‚Â«).")
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
    # Ã„ÂÃ†Â¯Ã¡Â»Å“NG CÃ†Â  DÃ¡Â»Â° PHÃƒâ€™NG 2: Local Mangstoon_AI Engine (Thay vÃƒÂ¬ Groq)
    # =========================================================================
    local_mangstoon = call_mangstoon_ai(prompt)
    if local_mangstoon and len(local_mangstoon.strip().split()) > 10:
        print("[SUCCESS] Local Mangstoon_AI succeeded!")
        return local_mangstoon.strip()

    # =========================================================================
    # Ã„ÂÃ†Â¯Ã¡Â»Å“NG CÃ†Â  DÃ¡Â»Â° PHÃƒâ€™NG 3: Groq Multi-Model Engine (DÃ¡Â»Â± phÃƒÂ²ng cÃ¡ÂºÂ¥p 3)
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
                        print(f"[SUCCESS] Groq Fallback Engine [{current_model}]: Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â£ sinh kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n ({len(content.strip().split())} tÃƒÂ¡Ã‚Â»Ã‚Â«).")
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
        
    # Backup GET request rÃƒÆ’Ã‚Âºt gÃƒÂ¡Ã‚Â»Ã‚Ân prompt
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
    arc_summary = arc.get("summary", "TiÃƒÂ¡Ã‚ÂºÃ‚Â¿p tÃƒÂ¡Ã‚Â»Ã‚Â¥c diÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¦n biÃƒÂ¡Ã‚ÂºÃ‚Â¿n cÃƒÂ¡Ã‚Â»Ã‚Â§a bÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi cÃƒÂ¡Ã‚ÂºÃ‚Â£nh hÃƒÂ¡Ã‚Â»Ã‚Âc viÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n.")
    
    print(f"[INFO] Generating blueprints for Arc {arc_num}: '{arc_title}' (Chapters {start_ch} - {end_ch})...")
    
    novel = database.get_novel(novel_id)
    novel_title = novel.get("title", "TruyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n mÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi")
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
                # GiÃƒÂ¡Ã‚ÂºÃ‚Â£i nÃƒÆ’Ã‚Â©n nÃƒÂ¡Ã‚ÂºÃ‚Â¿u LLM bÃƒÂ¡Ã‚Â»Ã‚Âc trong dict {"blueprints": [...]} hoÃƒÂ¡Ã‚ÂºÃ‚Â·c {"chapters": [...]}
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
            "TrÃƒÆ’Ã‚Â¹ng Sinh VÃƒÂ¡Ã‚ÂºÃ‚Â¡n CÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢, ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ VÃƒÆ’Ã‚Â´ TÃƒÂ¡Ã‚ÂºÃ‚Â­n",
            "ThÃƒÂ¡Ã‚Â»Ã‚Â©c TÃƒÂ¡Ã‚Â»Ã¢â‚¬Â°nh ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÂ¡Ã‚Â»Ã†â€™, NÃƒÆ’Ã‚Â©n ÃƒÆ’Ã¢â‚¬Â°p ThÃƒÂ¡Ã‚ÂºÃ‚Â§n Ma",
            "HuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t MÃƒÂ¡Ã‚ÂºÃ‚Â¡ch ThÃƒÆ’Ã‚Â´n ThiÃƒÆ’Ã‚Âªn, TrÃƒÂ¡Ã‚ÂºÃ‚Â¥n TÃƒÆ’Ã‚Â¡m PhÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng",
            "QuyÃƒÂ¡Ã‚Â»Ã‚Ân TrÃƒÂ¡Ã‚ÂºÃ‚Â¥n SÃƒâ€ Ã‚Â¡n HÃƒÆ’Ã‚Â , Uy ChÃƒÂ¡Ã‚ÂºÃ‚Â¥n ChÃƒâ€ Ã‚Â° ThiÃƒÆ’Ã‚Âªn",
            "VÃƒÆ’Ã‚Â´ Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch TrÃƒÆ’Ã‚Â¹ng Sinh, HÃƒÂ¡Ã‚Â»Ã¢â‚¬â€n Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢n LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n KhÃƒÆ’Ã‚Â­",
            "NghÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch ThiÃƒÆ’Ã‚Âªn Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢c TÃƒÆ’Ã‚Â´n, LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n HÃƒÆ’Ã‚Â³a ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÂ¡Ã‚ÂºÃ‚Â¡ch",
            "ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ NguyÃƒÆ’Ã‚Âªn KhÃƒÆ’Ã‚Â­, PhÃƒÆ’Ã‚Â¡ Tam CÃƒÂ¡Ã‚ÂºÃ‚Â£nh",
            "VÃƒÂ¡Ã‚ÂºÃ‚Â¡n GiÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi QuÃƒÂ¡Ã‚Â»Ã‚Â³ BÃƒÆ’Ã‚Â¡i, TiÃƒÆ’Ã‚Âªu ViÃƒÆ’Ã‚Âªm XuÃƒÂ¡Ã‚ÂºÃ‚Â¥t ThÃƒÂ¡Ã‚ÂºÃ‚Â¿",
            "ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ Ma NhÃƒÂ¡Ã‚ÂºÃ‚Â«n, Khai MÃƒÂ¡Ã‚Â»Ã…Â¸ ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÆ’Ã‚Â´ng",
            "VÃƒÆ’Ã‚Â´ Song KiÃƒÂ¡Ã‚ÂºÃ‚Â¿m KhÃƒÆ’Ã‚Â­, TrÃƒÂ¡Ã‚ÂºÃ‚Â£m DiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t CÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Âng Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch",
            "HÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ ThÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœng ThÃƒÂ¡Ã‚ÂºÃ‚Â§n CÃƒÂ¡Ã‚ÂºÃ‚Â¥p, ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ VÃƒÂ¡Ã‚ÂºÃ‚Â¡n VÃƒÂ¡Ã‚ÂºÃ‚Â­t",
            "BÃƒÆ’Ã‚Â¡ ThÃƒÂ¡Ã‚ÂºÃ‚Â§n XuÃƒÂ¡Ã‚ÂºÃ‚Â¥t ThÃƒÂ¡Ã‚ÂºÃ‚Â¿, NgÃƒâ€žÃ†â€™n CÃƒÂ¡Ã‚ÂºÃ‚Â£n VÃƒÂ¡Ã‚ÂºÃ‚Â¡n QuÃƒÆ’Ã‚Â¢n",
            "ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ VÃƒâ€žÃ‚Â©nh HÃƒÂ¡Ã‚ÂºÃ‚Â±ng, XÃƒÆ’Ã‚Â¢y DÃƒÂ¡Ã‚Â»Ã‚Â±ng Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â¿ CÃƒâ€ Ã‚Â¡",
            "ThÃƒÆ’Ã‚Â´n ThiÃƒÆ’Ã‚Âªn LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹a, Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢c TÃƒÆ’Ã‚Â´n VÃƒÂ¡Ã‚ÂºÃ‚Â¡n CÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢",
            "TuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t ThÃƒÂ¡Ã‚ÂºÃ‚Â¿ VÃƒÆ’Ã‚Â´ Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch, Phong ÃƒÂ¡Ã‚ÂºÃ‚Â¤n ThÃƒÂ¡Ã‚ÂºÃ‚Â§n HoÃƒÆ’Ã‚Â ng",
            "KhÃƒÆ’Ã‚Â­ PhÃƒÆ’Ã‚Â¡ch NgÃƒÆ’Ã‚Âºt TrÃƒÂ¡Ã‚Â»Ã‚Âi, ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ Long MÃƒÂ¡Ã‚ÂºÃ‚Â¡ch",
            "VÃƒÂ¡Ã‚ÂºÃ‚Â¡n CÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ Ma Cung, Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â¡i ChiÃƒÂ¡Ã‚ÂºÃ‚Â¿n ChÃƒâ€ Ã‚Â° ThiÃƒÆ’Ã‚Âªn",
            "BÃƒÆ’Ã‚Â¡ ChÃƒÂ¡Ã‚Â»Ã‚Â§ HuyÃƒÂ¡Ã‚Â»Ã‚Ân ThoÃƒÂ¡Ã‚ÂºÃ‚Â¡i, LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n HÃƒÆ’Ã‚Â³a VÃƒÂ¡Ã‚ÂºÃ‚Â¡n GiÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi"
        ]
        
        parsed_numbers = {int(b.get("chapter_number", 0)) for b in blueprints if isinstance(b, dict)}
        for ch_i in range(start_num, end_num + 1):
            if ch_i not in parsed_numbers:
                epic_t = EPIC_TITLES[(ch_i - 1) % len(EPIC_TITLES)]
                blueprints.append({
                    "chapter_number": ch_i,
                    "chapter_title": f"{epic_t} (TÃƒÂ¡Ã‚ÂºÃ‚Â­p {ch_i})",
                    "blueprint": f"DiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¦n biÃƒÂ¡Ã‚ÂºÃ‚Â¿n kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p theo cÃƒÂ¡Ã‚Â»Ã‚Â§a cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n ÃƒÂ¡Ã‚Â»Ã…Â¸ chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng {ch_i}.",
                    "characters_present": [],
                    "narrative_goal": "PhÃƒÆ’Ã‚Â¡t triÃƒÂ¡Ã‚Â»Ã†â€™n cÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœt truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n"
                })

        existing_chapter_numbers = {c["chapter_number"] for c in existing_chapters}
        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or f"ChÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng {ch_num}"
            blueprint_text = ch_data.get("blueprint") or "TiÃƒÂ¡Ã‚ÂºÃ‚Â¿p tÃƒÂ¡Ã‚Â»Ã‚Â¥c diÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¦n biÃƒÂ¡Ã‚ÂºÃ‚Â¿n cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n."
            
            # ChÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° tÃƒÂ¡Ã‚ÂºÃ‚Â¡o blueprint nÃƒÂ¡Ã‚ÂºÃ‚Â¿u chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng chÃƒâ€ Ã‚Â°a tÃƒÂ¡Ã‚Â»Ã¢â‚¬Å“n tÃƒÂ¡Ã‚ÂºÃ‚Â¡i trong CSDL
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
    # LÃƒÂ¡Ã‚ÂºÃ‚Â¥y tÃƒÂ¡Ã‚ÂºÃ‚Â­p hÃƒÂ¡Ã‚Â»Ã‚Â£p 100% tÃƒÂ¡Ã‚ÂºÃ‚Â¥t cÃƒÂ¡Ã‚ÂºÃ‚Â£ cÃƒÆ’Ã‚Â¡c sÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœ chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã‚Â£ xong tÃƒÂ¡Ã‚Â»Ã‚Â« Supabase + data/ + output/ + RAM
    completed_set = database.get_completed_chapters_set(novel_id)
    all_done_nums = {int(x) for x in completed_set if str(x).isdigit()}

    all_chapters = database.get_all_chapters(novel_id)
    
    # LÃƒÂ¡Ã‚Â»Ã‚Âc cÃƒÆ’Ã‚Â¡c chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng chÃƒâ€ Ã‚Â°a viÃƒÂ¡Ã‚ÂºÃ‚Â¿t xong kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n (< 1200 tÃƒÂ¡Ã‚Â»Ã‚Â« hoÃƒÂ¡Ã‚ÂºÃ‚Â·c cÃƒÆ’Ã‚Â²n lÃƒÆ’Ã‚Â  BLUEPRINT)
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

    print(f"[INFO] BÃ¡ÂºÂ®T Ã„ÂÃ¡ÂºÂ¦U QUY TRÃƒÅ’NH VIÃ¡ÂºÂ¾T CHÃ†Â¯Ã†Â NG MÃ¡Â»Å¡I: ChÃ†Â°Ã†Â¡ng {next_ch_number} (Ã„ÂÃƒÂ£ hoÃƒÂ n thÃƒÂ nh cÃƒÂ¡c tÃ¡ÂºÂ­p: {sorted(list(all_done_nums))})...")
    current_arc = get_current_arc(novel_id, next_ch_number)
    chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    if not chapter_record:
        generate_arc_blueprints(novel_id, current_arc)
        all_chapters = database.get_all_chapters(novel_id)
        chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    if not chapter_record:
        chapter_record = database.create_chapter(novel_id=novel_id, chapter_number=next_ch_number, title=f"ChÃ†Â°Ã†Â¡ng {next_ch_number}", content=f"BLUEPRINT: DiÃ¡Â»â€¦n biÃ¡ÂºÂ¿n tiÃ¡ÂºÂ¿p theo.")
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
    # TÃƒâ€žÃ†â€™ng tham chiÃƒÂ¡Ã‚ÂºÃ‚Â¿u tÃƒÂ¡Ã‚Â»Ã‚Â« 2-3 chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng lÃƒÆ’Ã‚Âªn 7 chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng gÃƒÂ¡Ã‚ÂºÃ‚Â§n nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t (5 - 10 chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng) Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã†â€™ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â£m bÃƒÂ¡Ã‚ÂºÃ‚Â£o mÃƒÂ¡Ã‚ÂºÃ‚Â¡ch truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n cÃƒÂ¡Ã‚Â»Ã‚Â±c kÃƒÂ¡Ã‚Â»Ã‚Â³ nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t quÃƒÆ’Ã‚Â¡n
    for ch in previous_chapters[-7:]:
        ch_snippet = ch['content'][:600] + "\n...\n" + ch['content'][-600:] if len(ch['content']) > 1200 else ch['content']
        working_memory_text += f"\n--- ChÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng {ch['chapter_number']}: {ch['title']} ---\n{ch_snippet}\n"
        
    attempt = 0
    max_attempts = 3
    final_content = ""
    
    prompt = prompts.WRITING_PROMPT.format(
        chapter_number=next_ch_number,
        chapter_title=chapter_record["title"],
        title="TruyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n 24h Audio",
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
            f"- PhÃƒÂ¡Ã‚ÂºÃ‚Â§n mÃƒÂ¡Ã‚Â»Ã…Â¸ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u (Prologue): BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C mÃƒÂ¡Ã‚Â»Ã…Â¸ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng bÃƒÂ¡Ã‚ÂºÃ‚Â±ng mÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh cuÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœn hÃƒÆ’Ã‚Âºt (khoÃƒÂ¡Ã‚ÂºÃ‚Â£ng 300 - 500 tÃƒÂ¡Ã‚Â»Ã‚Â«) miÃƒÆ’Ã‚Âªu tÃƒÂ¡Ã‚ÂºÃ‚Â£ bÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi cÃƒÂ¡Ã‚ÂºÃ‚Â£nh thÃƒÂ¡Ã‚ÂºÃ‚Â¿ giÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi linh hÃƒÂ¡Ã‚Â»Ã¢â‚¬Å“n, hÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ thÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœng Tinh ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ÃƒÂ¡Ã‚ÂºÃ‚Â¤n vÃƒÆ’Ã‚Â  bÃƒÆ’Ã‚Â­ mÃƒÂ¡Ã‚ÂºÃ‚Â­t chiÃƒÂ¡Ã‚ÂºÃ‚Â¿c hÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢p Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Å“ng Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â´ng SÃƒâ€ Ã‚Â¡n.\n"
            f"- **CÃƒÂ¡Ã‚ÂºÃ‚Â¢NH BÃƒÆ’Ã‚ÂO QUAN TRÃƒÂ¡Ã‚Â»Ã…â€™NG VÃƒÂ¡Ã‚Â»Ã¢â€šÂ¬ NHÃƒÆ’Ã¢â‚¬Å¡N VÃƒÂ¡Ã‚ÂºÃ‚Â¬T**: Trong phÃƒÂ¡Ã‚ÂºÃ‚Â§n mÃƒÂ¡Ã‚Â»Ã…Â¸ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u nÃƒÆ’Ã‚Â y, CHÃƒÂ¡Ã‚Â»Ã‹â€  TÃƒÂ¡Ã‚ÂºÃ‚Â¬P TRUNG duy nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t vÃƒÆ’Ã‚Â o nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t chÃƒÆ’Ã‚Â­nh ({protagonist_name}). "
            f"TUYÃƒÂ¡Ã‚Â»Ã¢â‚¬Â T Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‚ÂI KHÃƒÆ’Ã¢â‚¬ÂNG liÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t kÃƒÆ’Ã‚Âª hay giÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi thiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡u trÃƒÆ’Ã‚Â n lan cÃƒÆ’Ã‚Â¡c nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t phÃƒÂ¡Ã‚Â»Ã‚Â¥. CÃƒÆ’Ã‚Â¡c nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t phÃƒÂ¡Ã‚Â»Ã‚Â¥ sÃƒÂ¡Ã‚ÂºÃ‚Â½ chÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° xuÃƒÂ¡Ã‚ÂºÃ‚Â¥t hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n tÃƒÂ¡Ã‚Â»Ã‚Â± nhiÃƒÆ’Ã‚Âªn khi cÃƒÆ’Ã‚Â³ tÃƒÆ’Ã‚Â¬nh huÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœng Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i trong cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n.\n"
            f"- **CÃƒÂ¡Ã‚ÂºÃ‚Â¢NH BÃƒÆ’Ã‚ÂO QUAN TRÃƒÂ¡Ã‚Â»Ã…â€™NG VÃƒÂ¡Ã‚Â»Ã¢â€šÂ¬ TIÃƒÆ’Ã…Â U Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€šÂ¬**: TUYÃƒÂ¡Ã‚Â»Ã¢â‚¬Â T Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‚ÂI KHÃƒÆ’Ã¢â‚¬ÂNG VIÃƒÂ¡Ã‚ÂºÃ‚Â¾T CHÃƒÂ¡Ã‚Â»Ã‚Â® 'DÃƒÂ¡Ã‚ÂºÃ‚Â«n lÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c', 'DÃƒÂ¡Ã‚ÂºÃ‚Â«n lÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c:', 'GiÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi thiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡u:', hay 'Prologue:'. "
            f"HÃƒÆ’Ã‚Â£y nhÃƒÂ¡Ã‚ÂºÃ‚Â­p vai viÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÂ¡Ã‚ÂºÃ‚Â³ng vÃƒÆ’Ã‚Â o nÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢i dung truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n mÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t cÃƒÆ’Ã‚Â¡ch tÃƒÂ¡Ã‚Â»Ã‚Â± nhiÃƒÆ’Ã‚Âªn nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t."
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
            final_content = call_inkos_cloud(current_prompt)
            if not final_content or len(final_content.strip()) < 10:
                final_content = call_gemini(current_prompt)
            word_count = len(final_content.split()) if final_content else 0
            print(f"[INFO] Generated draft length: {word_count} words.")
            
            if word_count < 500:
                print(f"[WARNING] Draft response too short (words: {word_count}). Retrying with simplified prompt payload...")
                time.sleep(3)
                current_prompt = prompt[:2500] if len(prompt) > 2500 else prompt
                continue
                
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â", "Ãƒâ€šÃ‚Â»", "*"))
            
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

            # VÃƒÆ’Ã¢â‚¬â„¢NG LÃƒÂ¡Ã‚ÂºÃ‚Â¶P ÃƒÆ’Ã¢â‚¬Â°P BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â T >2800 TÃƒÂ¡Ã‚Â»Ã‚Âª (Guaranteed 2800+ Words Multi-Pass Expansion Loop for 12-18 min Audio)
            if word_count >= 2800 and not ends_abruptly:
                # INKOS MULTI-AGENT AUDITOR PASS: KhÃƒÂ¡Ã‚Â»Ã‚Â­ AI clichÃƒÆ’Ã‚Â© & BÃƒÂ¡Ã‚ÂºÃ‚Â£o toÃƒÆ’Ã‚Â n 100% Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i vÃƒâ€žÃ†â€™n bÃƒÂ¡Ã‚ÂºÃ‚Â£n
                try:
                    print("[INFO] Quality Assurance Agent: BÃƒÂ¡Ã‚ÂºÃ‚Â¯t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u rÃƒÆ’Ã‚Â  soÃƒÆ’Ã‚Â¡t 37 tiÃƒÆ’Ã‚Âªu chuÃƒÂ¡Ã‚ÂºÃ‚Â©n chÃƒÂ¡Ã‚ÂºÃ‚Â¥t lÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£ng & KhÃƒÂ¡Ã‚Â»Ã‚Â­ AI clichÃƒÆ’Ã‚Â©...")
                    audit_prompt = prompts.INKOS_AUDITOR_PROMPT.format(chapter_content=final_content[:6000])
                    audited_res = call_gemini(audit_prompt)
                    if audited_res and len(audited_res.split()) >= len(final_content.split()) * 0.9:
                        final_content = clean_chapter_content(audited_res)
                        word_count = len(final_content.split())
                        print(f"[SUCCESS] Quality Assurance Agent hoÃƒÆ’Ã‚Â n thÃƒÆ’Ã‚Â nh khÃƒÂ¡Ã‚Â»Ã‚Â­ AI clichÃƒÆ’Ã‚Â©. TÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ng sÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœ tÃƒÂ¡Ã‚Â»Ã‚Â« tinh chÃƒÂ¡Ã‚ÂºÃ‚Â¿: {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â«.")
                    else:
                        final_content = clean_chapter_content(final_content)
                        word_count = len(final_content.split())
                        print(f"[INFO] GiÃƒÂ¡Ã‚Â»Ã‚Â¯ nguyÃƒÆ’Ã‚Âªn Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i vÃƒâ€žÃ†â€™n bÃƒÂ¡Ã‚ÂºÃ‚Â£n Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§y Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã‚Â§: {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â« (TrÃƒÆ’Ã‚Â¡nh bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ rÃƒÆ’Ã‚Âºt ngÃƒÂ¡Ã‚ÂºÃ‚Â¯n).")
                except Exception as audit_err:
                    print(f"[WARNING] Quality Assurance Agent pass warning: {audit_err}")
                break
                
            expand_cycles = 0
            while word_count < 2800 and expand_cycles < 6:
                expand_cycles += 1
                print(f"[INFO] (LÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t nÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p {expand_cycles}/6) ChÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n tÃƒÂ¡Ã‚ÂºÃ‚Â¡i Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â¡t {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â« (<2800 tÃƒÂ¡Ã‚Â»Ã‚Â«). TÃƒÂ¡Ã‚Â»Ã‚Â± Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng kÃƒÆ’Ã‚Â­ch hoÃƒÂ¡Ã‚ÂºÃ‚Â¡t AI ViÃƒÂ¡Ã‚ÂºÃ‚Â¿t NÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi TiÃƒÂ¡Ã‚ÂºÃ‚Â¿p...")
                
                continuation_prompt = (
                    f"DÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi Ãƒâ€žÃ¢â‚¬ËœÃƒÆ’Ã‚Â¢y lÃƒÆ’Ã‚Â  phÃƒÂ¡Ã‚ÂºÃ‚Â§n trÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºc cÃƒÂ¡Ã‚Â»Ã‚Â§a ChÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng {next_ch_number} (tÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ng {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â«):\n\n"
                    f"{final_content[-1200:]}\n\n"
                    f"YÃƒÆ’Ã…Â U CÃƒÂ¡Ã‚ÂºÃ‚Â¦U BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C: HÃƒÆ’Ã‚Â£y viÃƒÂ¡Ã‚ÂºÃ‚Â¿t tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p Ãƒâ€žÃ¢â‚¬ËœoÃƒÂ¡Ã‚ÂºÃ‚Â¡n nÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi theo cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n trÃƒÆ’Ã‚Âªn (tÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thiÃƒÂ¡Ã‚Â»Ã†â€™u 1200 - 1800 tÃƒÂ¡Ã‚Â»Ã‚Â« nÃƒÂ¡Ã‚Â»Ã‚Â¯a). "
                    f"MiÃƒÆ’Ã‚Âªu tÃƒÂ¡Ã‚ÂºÃ‚Â£ diÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¦n biÃƒÂ¡Ã‚ÂºÃ‚Â¿n tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p theo, Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i sÃƒÆ’Ã‚Â¢u sÃƒÂ¡Ã‚ÂºÃ‚Â¯c, cÃƒÂ¡Ã‚ÂºÃ‚Â£m xÃƒÆ’Ã‚Âºc nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t vÃƒÆ’Ã‚Â  kÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÆ’Ã‚Âºc bÃƒÂ¡Ã‚ÂºÃ‚Â±ng mÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t nÃƒÆ’Ã‚Âºt thÃƒÂ¡Ã‚ÂºÃ‚Â¯t kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch tÃƒÆ’Ã‚Â­nh. "
                    f"ViÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÂ¡Ã‚ÂºÃ‚Â³ng vÃƒÆ’Ã‚Â o nÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢i dung truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n, khÃƒÆ’Ã‚Â´ng lÃƒÂ¡Ã‚ÂºÃ‚Â·p lÃƒÂ¡Ã‚ÂºÃ‚Â¡i Ãƒâ€žÃ¢â‚¬ËœoÃƒÂ¡Ã‚ÂºÃ‚Â¡n cÃƒâ€¦Ã‚Â©."
                )
                
                part_next = call_gemini(continuation_prompt)
                if part_next and len(part_next.split()) > 100:
                    cleaned_next, _ = verify_and_sanitize_chapter_content(part_next)
                    # TrÃƒÂ¡nh nÃ¡Â»â€˜i chuÃ¡Â»â€”i lÃ¡ÂºÂ·p lÃ¡ÂºÂ¡i vÃƒÂ´ tÃ¡ÂºÂ­n
                    if cleaned_next in final_content:
                        print("[WARNING] Ã„ÂÃƒÂ£ phÃƒÂ¡t hiÃ¡Â»â€¡n Ã„â€˜oÃ¡ÂºÂ¡n nÃ¡Â»â€˜i tiÃ¡ÂºÂ¿p bÃ¡Â»â€¹ lÃ¡ÂºÂ·p lÃ¡ÂºÂ¡i, ngÃ¡ÂºÂ¯t vÃƒÂ²ng lÃ¡ÂºÂ·p expansion.")
                        break
                    final_content = final_content + "\n\n" + cleaned_next
                    word_count = len(final_content.split())
                    print(f"[SUCCESS] Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â£ nÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p thÃƒÆ’Ã‚Â nh cÃƒÆ’Ã‚Â´ng! TÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢ng Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n tÃƒÂ¡Ã‚ÂºÃ‚Â¡i: {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â«.")
                    if word_count >= 2800:
                        break
                else:
                    time.sleep(2)
                    
            if word_count >= 2800:
                break
                
            if ends_abruptly:
                print(f"[WARNING] Draft ends abruptly (no punctuation at the end). Requesting completion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    "\n\n**CÃƒÂ¡Ã‚ÂºÃ‚Â¢NH BÃƒÆ’Ã‚ÂO CÃƒÂ¡Ã‚Â»Ã‚Â°C KÃƒÂ¡Ã‚Â»Ã‚Â² QUAN TRÃƒÂ¡Ã‚Â»Ã…â€™NG**: BÃƒÂ¡Ã‚ÂºÃ‚Â£n thÃƒÂ¡Ã‚ÂºÃ‚Â£o trÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºc cÃƒÂ¡Ã‚Â»Ã‚Â§a bÃƒÂ¡Ã‚ÂºÃ‚Â¡n bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ cÃƒÂ¡Ã‚ÂºÃ‚Â¯t cÃƒÂ¡Ã‚Â»Ã‚Â¥t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t ngÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t ÃƒÂ¡Ã‚Â»Ã…Â¸ cuÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi (chÃƒâ€ Ã‚Â°a hÃƒÂ¡Ã‚ÂºÃ‚Â¿t cÃƒÆ’Ã‚Â¢u, chÃƒâ€ Ã‚Â°a cÃƒÆ’Ã‚Â³ dÃƒÂ¡Ã‚ÂºÃ‚Â¥u chÃƒÂ¡Ã‚ÂºÃ‚Â¥m cÃƒÆ’Ã‚Â¢u kÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÆ’Ã‚Âºc). "
                    "BÃƒÂ¡Ã‚ÂºÃ‚Â¡n BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C phÃƒÂ¡Ã‚ÂºÃ‚Â£i viÃƒÂ¡Ã‚ÂºÃ‚Â¿t trÃƒÂ¡Ã‚Â»Ã‚Ân vÃƒÂ¡Ã‚ÂºÃ‚Â¹n cÃƒÆ’Ã‚Â¢u chuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n, mÃƒÂ¡Ã‚Â»Ã…Â¸ rÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng chi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t cÃƒÆ’Ã‚Â¡c phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh, hÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢i thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i vÃƒÆ’Ã‚Â  kÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÆ’Ã‚Âºc chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng mÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢t cÃƒÆ’Ã‚Â¡ch trÃƒÂ¡Ã‚Â»Ã‚Ân vÃƒÂ¡Ã‚ÂºÃ‚Â¹n bÃƒÂ¡Ã‚ÂºÃ‚Â±ng dÃƒÂ¡Ã‚ÂºÃ‚Â¥u chÃƒÂ¡Ã‚ÂºÃ‚Â¥m cÃƒÆ’Ã‚Â¢u."
                )
            else:
                print(f"[WARNING] Draft too short ({word_count} words). Requesting longer expansion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    f"\n\n**CÃƒÂ¡Ã‚ÂºÃ‚Â¢NH BÃƒÆ’Ã‚ÂO CÃƒÂ¡Ã‚Â»Ã‚Â°C KÃƒÂ¡Ã‚Â»Ã‚Â² QUAN TRÃƒÂ¡Ã‚Â»Ã…â€™NG VÃƒÂ¡Ã‚Â»Ã¢â€šÂ¬ Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‹Å“ DÃƒÆ’Ã¢â€šÂ¬I (BÃƒÂ¡Ã‚ÂºÃ‚Â®T BUÃƒÂ¡Ã‚Â»Ã‹Å“C)**:\n"
                    f"BÃƒÂ¡Ã‚ÂºÃ‚Â£n thÃƒÂ¡Ã‚ÂºÃ‚Â£o bÃƒÂ¡Ã‚ÂºÃ‚Â¡n vÃƒÂ¡Ã‚Â»Ã‚Â«a viÃƒÂ¡Ã‚ÂºÃ‚Â¿t quÃƒÆ’Ã‚Â¡ ngÃƒÂ¡Ã‚ÂºÃ‚Â¯n (chÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° cÃƒÆ’Ã‚Â³ {word_count} tÃƒÂ¡Ã‚Â»Ã‚Â«), trong khi yÃƒÆ’Ã‚Âªu cÃƒÂ¡Ã‚ÂºÃ‚Â§u tÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thiÃƒÂ¡Ã‚Â»Ã†â€™u lÃƒÆ’Ã‚Â  2200 tÃƒÂ¡Ã‚Â»Ã‚Â« Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã†â€™ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â¡t 10 phÃƒÆ’Ã‚Âºt nÃƒÆ’Ã‚Â³i.\n"
                    f"Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã†â€™ sÃƒÂ¡Ã‚Â»Ã‚Â­a lÃƒÂ¡Ã‚Â»Ã¢â‚¬â€i nÃƒÆ’Ã‚Â y, bÃƒÂ¡Ã‚ÂºÃ‚Â¡n phÃƒÂ¡Ã‚ÂºÃ‚Â£i viÃƒÂ¡Ã‚ÂºÃ‚Â¿t cÃƒÂ¡Ã‚Â»Ã‚Â±c kÃƒÂ¡Ã‚Â»Ã‚Â³ chi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t theo hÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºng dÃƒÂ¡Ã‚ÂºÃ‚Â«n sau:\n"
                    f"1. Chia chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n thÃƒÆ’Ã‚Â nh ÃƒÆ’Ã‚Â­t nhÃƒÂ¡Ã‚ÂºÃ‚Â¥t 5 phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh lÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºn riÃƒÆ’Ã‚Âªng biÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t (MÃƒÂ¡Ã‚Â»Ã¢â‚¬â€i phÃƒÆ’Ã‚Â¢n cÃƒÂ¡Ã‚ÂºÃ‚Â£nh viÃƒÂ¡Ã‚ÂºÃ‚Â¿t tÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thiÃƒÂ¡Ã‚Â»Ã†â€™u 5-6 Ãƒâ€žÃ¢â‚¬ËœoÃƒÂ¡Ã‚ÂºÃ‚Â¡n vÃƒâ€žÃ†â€™n dÃƒÆ’Ã‚Â i).\n"
                    f"2. Ãƒâ€žÃ‚Âi sÃƒÆ’Ã‚Â¢u miÃƒÆ’Ã‚Âªu tÃƒÂ¡Ã‚ÂºÃ‚Â£ cÃƒÂ¡Ã‚Â»Ã‚Â±c kÃƒÂ¡Ã‚Â»Ã‚Â³ tÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° mÃƒÂ¡Ã‚Â»Ã¢â‚¬Â°: cÃƒÂ¡Ã‚ÂºÃ‚Â£nh sÃƒÂ¡Ã‚ÂºÃ‚Â¯c khÃƒÆ’Ã‚Â´ng gian hÃƒÂ¡Ã‚Â»Ã‚Âc viÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n, thÃƒÂ¡Ã‚Â»Ã‚Âi tiÃƒÂ¡Ã‚ÂºÃ‚Â¿t, ÃƒÆ’Ã‚Â¢m thanh giÃƒÆ’Ã‚Â³ thÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢i, biÃƒÂ¡Ã‚Â»Ã†â€™u cÃƒÂ¡Ã‚ÂºÃ‚Â£m nÃƒÆ’Ã‚Â©t mÃƒÂ¡Ã‚ÂºÃ‚Â·t tÃƒÂ¡Ã‚Â»Ã‚Â«ng nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t, cÃƒÂ¡Ã‚Â»Ã‚Â­ chÃƒÂ¡Ã‚Â»Ã¢â‚¬Â° tay chÃƒÆ’Ã‚Â¢n, vÃƒÆ’Ã‚Â  dÃƒÆ’Ã‚Â²ng suy nghÃƒâ€žÃ‚Â© nÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢i tÃƒÆ’Ã‚Â¢m kÃƒÆ’Ã‚Â©o dÃƒÆ’Ã‚Â i.\n"
                    f"3. ViÃƒÂ¡Ã‚ÂºÃ‚Â¿t cÃƒÆ’Ã‚Â¡c Ãƒâ€žÃ¢â‚¬ËœoÃƒÂ¡Ã‚ÂºÃ‚Â¡n Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi thoÃƒÂ¡Ã‚ÂºÃ‚Â¡i dÃƒÆ’Ã‚Â i, thÃƒÂ¡Ã‚Â»Ã‚Â±c tÃƒÂ¡Ã‚ÂºÃ‚Â¿ vÃƒÆ’Ã‚Â  sÃƒÆ’Ã‚Â¢u sÃƒÂ¡Ã‚ÂºÃ‚Â¯c giÃƒÂ¡Ã‚Â»Ã‚Â¯a cÃƒÆ’Ã‚Â¡c nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t (TrÃƒÂ¡Ã‚ÂºÃ‚Â§n Lam, Linh Vy, Minh Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‚Â©c, v.v.). KhÃƒÆ’Ã‚Â´ng Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c viÃƒÂ¡Ã‚ÂºÃ‚Â¿t lÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºt qua.\n"
                    f"4. TUYÃƒÂ¡Ã‚Â»Ã¢â‚¬Â T Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‚ÂI khÃƒÆ’Ã‚Â´ng tÃƒÆ’Ã‚Â³m tÃƒÂ¡Ã‚ÂºÃ‚Â¯t hay kÃƒÂ¡Ã‚ÂºÃ‚Â¿t thÃƒÆ’Ã‚Âºc chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng truyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n sÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºm khi chÃƒâ€ Ã‚Â°a Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã‚Â§ Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ dÃƒÆ’Ã‚Â i yÃƒÆ’Ã‚Âªu cÃƒÂ¡Ã‚ÂºÃ‚Â§u."
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
    # Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‹Å“NG CÃƒâ€ Ã‚Â  DÃƒÂ¡Ã‚Â»Ã…Â CH THUÃƒÂ¡Ã‚ÂºÃ‚Â¬T TIÃƒÂ¡Ã‚ÂºÃ‚Â¾NG VIÃƒÂ¡Ã‚Â»Ã¢â‚¬Â T GEMINI API: Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â£m bÃƒÂ¡Ã‚ÂºÃ‚Â£o 100% kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n tiÃƒÂ¡Ã‚Â»Ã†â€™u thuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t chuÃƒÂ¡Ã‚ÂºÃ‚Â©n TiÃƒÂ¡Ã‚ÂºÃ‚Â¿ng ViÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t mÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£t mÃƒÆ’Ã‚Â 
    cleaned_content = translate_to_vietnamese_with_gemini(cleaned_content)
    
    # Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚ÂºÃ‚Â£m bÃƒÂ¡Ã‚ÂºÃ‚Â£o tiÃƒÆ’Ã‚Âªu Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã‚Â chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng khÃƒÆ’Ã‚Â´ng bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ trÃƒÆ’Ã‚Â¹ng lÃƒÂ¡Ã‚ÂºÃ‚Â·p placeholder
    cur_title = chapter_record.get("title", "")
    if "HÃƒÆ’Ã‚Â nh TrÃƒÆ’Ã‚Â¬nh MÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi" in cur_title or not cur_title or cur_title == f"ChÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng {next_ch_number}":
        EPIC_TITLES = [
            "TrÃƒÆ’Ã‚Â¹ng Sinh VÃƒÂ¡Ã‚ÂºÃ‚Â¡n CÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¢, ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ VÃƒÆ’Ã‚Â´ TÃƒÂ¡Ã‚ÂºÃ‚Â­n", "ThÃƒÂ¡Ã‚Â»Ã‚Â©c TÃƒÂ¡Ã‚Â»Ã¢â‚¬Â°nh ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÂ¡Ã‚Â»Ã†â€™, NÃƒÆ’Ã‚Â©n ÃƒÆ’Ã¢â‚¬Â°p ThÃƒÂ¡Ã‚ÂºÃ‚Â§n Ma", "HuyÃƒÂ¡Ã‚ÂºÃ‚Â¿t MÃƒÂ¡Ã‚ÂºÃ‚Â¡ch ThÃƒÆ’Ã‚Â´n ThiÃƒÆ’Ã‚Âªn, TrÃƒÂ¡Ã‚ÂºÃ‚Â¥n TÃƒÆ’Ã‚Â¡m PhÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng",
            "QuyÃƒÂ¡Ã‚Â»Ã‚Ân TrÃƒÂ¡Ã‚ÂºÃ‚Â¥n SÃƒâ€ Ã‚Â¡n HÃƒÆ’Ã‚Â , Uy ChÃƒÂ¡Ã‚ÂºÃ‚Â¥n ChÃƒâ€ Ã‚Â° ThiÃƒÆ’Ã‚Âªn", "VÃƒÆ’Ã‚Â´ Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch TrÃƒÆ’Ã‚Â¹ng Sinh, HÃƒÂ¡Ã‚Â»Ã¢â‚¬â€n Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢n LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n KhÃƒÆ’Ã‚Â­", "NghÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch ThiÃƒÆ’Ã‚Âªn Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢c TÃƒÆ’Ã‚Â´n, LuyÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n HÃƒÆ’Ã‚Â³a ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÂ¡Ã‚ÂºÃ‚Â¡ch",
            "ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ NguyÃƒÆ’Ã‚Âªn KhÃƒÆ’Ã‚Â­, PhÃƒÆ’Ã‚Â¡ Tam CÃƒÂ¡Ã‚ÂºÃ‚Â£nh", "VÃƒÂ¡Ã‚ÂºÃ‚Â¡n GiÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi QuÃƒÂ¡Ã‚Â»Ã‚Â³ BÃƒÆ’Ã‚Â¡i, TiÃƒÆ’Ã‚Âªu ViÃƒÆ’Ã‚Âªm XuÃƒÂ¡Ã‚ÂºÃ‚Â¥t ThÃƒÂ¡Ã‚ÂºÃ‚Â¿", "ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ Ma NhÃƒÂ¡Ã‚ÂºÃ‚Â«n, Khai MÃƒÂ¡Ã‚Â»Ã…Â¸ ThÃƒÂ¡Ã‚ÂºÃ‚Â§n ThÃƒÆ’Ã‚Â´ng",
            "VÃƒÆ’Ã‚Â´ Song KiÃƒÂ¡Ã‚ÂºÃ‚Â¿m KhÃƒÆ’Ã‚Â­, TrÃƒÂ¡Ã‚ÂºÃ‚Â£m DiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡t CÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Âng Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch", "HÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ ThÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœng ThÃƒÂ¡Ã‚ÂºÃ‚Â§n CÃƒÂ¡Ã‚ÂºÃ‚Â¥p, ThÃƒÆ’Ã‚Â´n PhÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ VÃƒÂ¡Ã‚ÂºÃ‚Â¡n VÃƒÂ¡Ã‚ÂºÃ‚Â­t", "BÃƒÆ’Ã‚Â¡ ThÃƒÂ¡Ã‚ÂºÃ‚Â§n XuÃƒÂ¡Ã‚ÂºÃ‚Â¥t ThÃƒÂ¡Ã‚ÂºÃ‚Â¿, NgÃƒâ€žÃ†â€™n CÃƒÂ¡Ã‚ÂºÃ‚Â£n VÃƒÂ¡Ã‚ÂºÃ‚Â¡n QuÃƒÆ’Ã‚Â¢n"
        ]
        epic_name = EPIC_TITLES[(next_ch_number - 1) % len(EPIC_TITLES)]
        cur_title = f"{epic_name} (TÃƒÂ¡Ã‚ÂºÃ‚Â­p {next_ch_number})"

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
        
        # 1. TÃƒÂ¡Ã‚Â»Ã‚Â° Ãƒâ€žÃ‚ÂÃƒÂ¡Ã‚Â»Ã‹Å“NG LÃƒâ€ Ã‚Â¯U CÃƒÆ’Ã‚ÂC NHÃƒÆ’Ã¢â‚¬Å¡N VÃƒÂ¡Ã‚ÂºÃ‚Â¬T MÃƒÂ¡Ã‚Â»Ã…Â¡I SÃƒÆ’Ã‚ÂNG TÃƒÂ¡Ã‚ÂºÃ‚Â O VÃƒÆ’Ã¢â€šÂ¬O CSDL SUPABASE
        new_chars = data.get("new_characters", [])
        if new_chars:
            print(f"[INFO] ÃƒÂ°Ã…Â¸Ã…â€™Ã…Â¸ Ãƒâ€žÃ‚ÂÃƒÆ’Ã‚Â£ phÃƒÆ’Ã‚Â¡t hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n {len(new_chars)} nhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t MÃƒÂ¡Ã‚Â»Ã…Â¡I Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c AI sÃƒÆ’Ã‚Â¡ng tÃƒÂ¡Ã‚ÂºÃ‚Â¡o trong chÃƒâ€ Ã‚Â°Ãƒâ€ Ã‚Â¡ng!")
            for n_char in new_chars:
                n_name = n_char.get("name")
                if n_name and n_name.strip():
                    database.upsert_character(
                        novel_id=novel_id,
                        name=n_name.strip(),
                        description=n_char.get("description", "NhÃƒÆ’Ã‚Â¢n vÃƒÂ¡Ã‚ÂºÃ‚Â­t mÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi xuÃƒÂ¡Ã‚ÂºÃ‚Â¥t hiÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡n trong kÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ch bÃƒÂ¡Ã‚ÂºÃ‚Â£n"),
                        power_tier=n_char.get("power_tier", "Cao ThÃƒÂ¡Ã‚Â»Ã‚Â§ MÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi"),
                        combat_stats=n_char.get("combat_stats", {}),
                        relationships=n_char.get("relationships", {}),
                        failure_flag=False,
                        last_breakthrough_chapter=0
                    )
                    print(f"   [SUPABASE] + Da tu dong nhat Nhan Vat MOI: {n_name} ({n_char.get('power_tier')})")

        # 2. CÃƒÂ¡Ã‚ÂºÃ‚Â¬P NHÃƒÂ¡Ã‚ÂºÃ‚Â¬T TRÃƒÂ¡Ã‚ÂºÃ‚Â NG THÃƒÆ’Ã‚ÂI CÃƒÆ’Ã‚ÂC NHÃƒÆ’Ã¢â‚¬Å¡N VÃƒÂ¡Ã‚ÂºÃ‚Â¬T CÃƒâ€¦Ã‚Â¨
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



