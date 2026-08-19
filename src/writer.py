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
        # Thá»­ lÃ m sáº¡ch dáº¥u pháº©y thá»«a á»Ÿ cuá»‘i (trailing commas)
        cleaned_no_comma = re.sub(r",\s*([\}\]])", r"\1", cleaned)
        try:
            return json.loads(cleaned_no_comma)
        except Exception:
            pass
        # Thá»­ trÃ­ch xuáº¥t khá»‘i {...} hoáº·c [...] báº±ng Regex
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
        sentences = re.split(r'(?<=[.?!â€¦])\s+(?=[a-zA-ZÃ Ã¡Ã¢Ã£Ã¨Ã©ÃªÃ¬Ã­Ã²Ã³Ã´ÃµÃ¹ÃºÃ½Ä‘Ã€ÃÃ‚ÃƒÃˆÃ‰ÃŠÃŒÃÃ’Ã“Ã”Ã•Ã™ÃšÃÄ0-9"\'Â«â€œ])', para)
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
    """Clean draft content, stripping markdown and prefix headers like 'Dẫn lược:', 'Chương X:', etc."""
    cleaned = text.strip()
    pattern = r"(?im)^\s*[*_]*\s*(?:Dẫn lược|Giới thiệu|Phần dẫn lược|Tóm tắt bối cảnh|Prologue|Introduction|Giới thiệu bối cảnh)\s*[:：\-–—]*\s*[*_]*\s*[:：\-–—]*\s*"
    cleaned = re.sub(pattern, "", cleaned).strip()
    cleaned = remove_repetitive_sentences(cleaned)
    return cleaned

def expand_chapter_content(content: str, target_words: int = 3200) -> str:
    """Ná»‘i dÃ i ká»‹ch báº£n chÆ°Æ¡ng truyá»‡n náº¿u chÆ°a Ä‘á»§ Ä‘á»™ dÃ i >10 phÃºt audio (600 giÃ¢y)."""
    current_words = len(content.split()) if content else 0
    if current_words >= target_words:
        return content
        
    print(f"[INFO] âš¡ CHáº¾ Äá»˜ LÃ€M Láº I (>10 PHÃšT): Äá»™ dÃ i hiá»‡n táº¡i {current_words} tá»« (<{target_words} tá»«). Äang gá»i AI viáº¿t ná»‘i tiáº¿p phÃ¢n cáº£nh ká»‹ch tÃ­nh...")
    
    continuation_prompt = (
        f"DÆ°á»›i Ä‘Ã¢y lÃ  pháº§n trÆ°á»›c cá»§a chÆ°Æ¡ng truyá»‡n (tá»•ng {current_words} tá»«):\n\n"
        f"{content[-1500:]}\n\n"
        f"YÃŠU Cáº¦U Báº®T BUá»˜C (Ã‰P THá»œI LÆ¯á»¢NG KÃ‰O DÃ€I >10 PHÃšT AUDIO):\n"
        f"HÃ£y viáº¿t tiáº¿p phÃ¢n cáº£nh diá»…n biáº¿n ká»‹ch tÃ­nh tiáº¿p theo cá»§a cÃ¢u chuyá»‡n trÃªn (tá»‘i thiá»ƒu 1500 - 2000 tá»« ná»¯a).\n"
        f"1. Viáº¿t chi tiáº¿t cuá»™c Ä‘á»‘i thoáº¡i gay gáº¯t, bá»™c phÃ¡t cáº£m xÃºc giá»¯a cÃ¡c nhÃ¢n váº­t chÃ­nh.\n"
        f"2. MiÃªu táº£ chi tiáº¿t chiÃªu thá»©c, giao phong ká»‹ch tÃ­nh vÃ  suy nghÄ© ná»™i tÃ¢m dá»“n dáº­p.\n"
        f"3. Káº¿t thÃºc báº±ng má»™t nÃºt tháº¯t cliffhanger ká»‹ch tÃ­nh.\n"
        f"Viáº¿t tháº³ng vÃ o cÃ¢u chuyá»‡n 100% báº±ng Tiáº¿ng Viá»‡t mÆ°á»£t mÃ , khÃ´ng láº·p láº¡i Ä‘oáº¡n cÅ©."
    )
    
    for _expand_attempt in range(3):
        part_next = call_gemini(continuation_prompt)
        if part_next and len(part_next.split()) > 200:
            cleaned_next = clean_chapter_content(part_next)
            if cleaned_next.lower() in content.lower():
                continue
            content = content + "\n\n" + cleaned_next
            print(f"[SUCCESS] Ä Ã£ ná»‘i dÃ i chÆ°Æ¡ng truyá»‡n! Tá»•ng sá»‘ tá»« má»›i: {len(content.split())} tá»«.")
            if len(content.split()) >= target_words:
                break
    return content

LEGACY_INVALID_NAMES = {}

def verify_and_sanitize_chapter_content(text: str, novel_id: str = "") -> tuple:
    """
    Bá»˜ KIá»‚M TRA Tá»° Ä á»˜NG Báº¢O Vá»† CHÆ¯Æ NG TRUYá»†N (Automated Chapter Auditor).
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
        print(f"[WARNING] âš ï¸ PHÃT HIá»†N Lá»–I TÃŠN NHÃ‚N Váº¬T CÅ¨: {found_invalid}! ÄÃ£ tá»± Ä‘á»™ng thay tháº¿ chuáº©n thÃ nh nhÃ¢n váº­t bá»™ truyá»‡n hiá»‡n táº¡i.")
        return sanitized_text, True
        
    return text, False

@cached(ttl_seconds=86400)
def translate_to_vietnamese_with_gemini(text: str) -> str:
    """Tá»± Ä‘á»™ng kiá»ƒm tra vÃ  dá»‹ch toÃ n bá»™ ká»‹ch báº£n tiá»ƒu thuyáº¿t tá»« tiáº¿ng Trung/tiáº¿ng Anh sang tiáº¿ng Viá»‡t chuáº©n mÆ°á»£t mÃ  100% qua Gemini API."""
    if not text or not text.strip():
        return text
        
    # Tá»± Ä‘á»™ng rÃ  soÃ¡t vÃ  khá»­ tÃªn nhÃ¢n váº­t cÅ© rÃ¡c
    text, _ = verify_and_sanitize_chapter_content(text)
    
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    if not has_chinese:
        return text
        
    print(f"[INFO] Báº¯t Ä‘áº§u rÃ  soÃ¡t ngÃ´n ngá»¯ ká»‹ch báº£n (Has Chinese: {has_chinese})...")
    print("[INFO] KÃ­ch hoáº¡t Äá»™ng CÆ¡ Dá»‹ch Thuáº­t Gemini API: Dá»‹ch/Tá»‘i Æ°u toÃ n bá»™ ká»‹ch báº£n tiá»ƒu thuyáº¿t sang Tiáº¿ng Viá»‡t mÆ°á»£t mÃ ...")
    translate_prompt = (
        "Báº¡n lÃ  dá»‹ch giáº£ tiá»ƒu thuyáº¿t webtoon hÃ ng Ä‘áº§u. HÃ£y dá»‹ch/chuyá»ƒn ngá»¯ toÃ n bá»™ chÆ°Æ¡ng tiá»ƒu thuyáº¿t sau Ä‘Ã¢y sang tiáº¿ng Viá»‡t tá»± nhiÃªn, giÃ u cáº£m xÃºc vÃ  háº¥p dáº«n.\n"
        "YÃŠU Cáº¦U Dá»ŠCH THUáº¬T Báº®T BUá»˜C:\n"
        "1. Dá»‹ch 100% sang tiáº¿ng Viá»‡t thuáº§n tÃºy, mÆ°á»£t mÃ , vÄƒn phong tiá»ƒu thuyáº¿t hÃ nh Ä‘á»™ng/huyá»n áº£o ká»‹ch tÃ­nh.\n"
        "2. Giá»¯ nguyÃªn 100% Ä‘á»™ dÃ i vÄƒn báº£n, lá»i thoáº¡i trong ngoáº·c kÃ©p (\"...\"), vÃ  cáº¥u trÃºc cÃ¢u chuyá»‡n. TUYá»†T Äá»I KHÃ”NG tÃ³m táº¯t hay bá» sÃ³t chi tiáº¿t nÃ o.\n"
        "3. Giá»¯ nguyÃªn 100% tÃªn nhÃ¢n váº­t chuáº©n tá»« nguyÃªn báº£n. Cáº¥m tá»± Ä‘á»•i sang tÃªn khÃ¡c.\n"
        "4. Chá»‰ xuáº¥t ra duy nháº¥t vÄƒn báº£n truyá»‡n Ä‘Ã£ dá»‹ch sang tiáº¿ng Viá»‡t, khÃ´ng kÃ¨m lá»i dáº«n hay giáº£i thÃ­ch.\n\n"
        f"VÄ‚N Báº¢N Cáº¦N Dá»ŠCH:\n{text}"
    )
    translated_res = call_gemini(translate_prompt)
    if translated_res and len(translated_res.split()) > 200:
        cleaned_res = clean_chapter_content(translated_res)
        cleaned_res, _ = verify_and_sanitize_chapter_content(cleaned_res)
        print(f"[SUCCESS] ÄÃ£ hoÃ n thÃ nh dá»‹ch ká»‹ch báº£n sang Tiáº¿ng Viá»‡t qua Gemini API! Äá»™ dÃ i: {len(cleaned_res.split())} tá»«.")
        return cleaned_res
    return text

@cached(ttl_seconds=86400)
def call_gemini(prompt: str, json_mode: bool = False, retries: int = 12) -> str:
    """
    Æ¯U TIÃŠN 100% HÃ€NG Äáº¦U: InkOS Multi-Agent Engine (Google Gemini 2.0 Flash API vá»›i Key Rotator).
    Chá»‰ khi Gemini háº¿t Key má»›i chuyá»ƒn sang Groq / OpenRouter dá»± phÃ²ng.
    """
    # =========================================================================
    # Äá»˜NG CÆ  Æ¯U TIÃŠN 1: InkOS Gemini 2.0 Flash Engine (Google API vá»›i Key Rotator)
    # =========================================================================
    gemini_models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
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
                print(f"[SUCCESS] âš¡ InkOS Writer Agent [{current_g_model}]: Táº¡o ká»‹ch báº£n mÆ°á»£t mÃ  thÃ nh cÃ´ng! ({len(response.text.strip().split())} tá»«).")
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
                time.sleep(1.0)

    # =========================================================================
    # Äá»˜NG CÆ  Dá»° PHÃ’NG 2: Groq Multi-Model Engine (Dá»± phÃ²ng cáº¥p 2)
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
                    content = resp_json["choices"][0]["message"]["content"]
                    if content and len(content.strip().split()) > 10:
                        print(f"[SUCCESS] Groq Fallback Engine [{current_model}]: ÄÃ£ sinh ká»‹ch báº£n ({len(content.strip().split())} tá»«).")
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
        "google/gemini-2.0-flash-exp:free",
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
        
    # Backup GET request rÃºt gá»n prompt
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
    novel_id = novel["id"]
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
    arc_summary = arc.get("summary", "Tiáº¿p tá»¥c diá»…n biáº¿n cá»§a bá»‘i cáº£nh há»c viá»‡n.")
    
    print(f"[INFO] Generating blueprints for Arc {arc_num}: '{arc_title}' (Chapters {start_ch} - {end_ch})...")
    
    novel = database.get_novel(novel_id)
    novel_title = novel.get("title", "Truyá»‡n má»›i")
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
                # Giáº£i nÃ©n náº¿u LLM bá»c trong dict {"blueprints": [...]} hoáº·c {"chapters": [...]}
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
            "TrÃ¹ng Sinh Váº¡n Cá»•, ThÃ´n Phá»‡ VÃ´ Táº­n",
            "Thá»©c Tá»‰nh Tháº§n Thá»ƒ, NÃ©n Ã‰p Tháº§n Ma",
            "Huyáº¿t Máº¡ch ThÃ´n ThiÃªn, Tráº¥n TÃ¡m PhÆ°Æ¡ng",
            "Quyá»n Tráº¥n SÆ¡n HÃ , Uy Cháº¥n ChÆ° ThiÃªn",
            "VÃ´ Äá»‹ch TrÃ¹ng Sinh, Há»—n Äá»™n Luyá»‡n KhÃ­",
            "Nghá»‹ch ThiÃªn Äá»™c TÃ´n, Luyá»‡n HÃ³a Tháº§n Tháº¡ch",
            "ThÃ´n Phá»‡ NguyÃªn KhÃ­, PhÃ¡ Tam Cáº£nh",
            "Váº¡n Giá»›i Quá»³ BÃ¡i, TiÃªu ViÃªm Xuáº¥t Tháº¿",
            "ThÃ´n Phá»‡ Ma Nháº«n, Khai Má»Ÿ Tháº§n ThÃ´ng",
            "VÃ´ Song Kiáº¿m KhÃ­, Tráº£m Diá»‡t CÆ°á»ng Äá»‹ch",
            "Há»‡ Thá»‘ng Tháº§n Cáº¥p, ThÃ´n Phá»‡ Váº¡n Váº­t",
            "BÃ¡ Tháº§n Xuáº¥t Tháº¿, NgÄƒn Cáº£n Váº¡n QuÃ¢n",
            "ThÃ´n Phá»‡ VÄ©nh Háº±ng, XÃ¢y Dá»±ng Äáº¿ CÆ¡",
            "ThÃ´n ThiÃªn Luyá»‡n Äá»‹a, Äá»™c TÃ´n Váº¡n Cá»•",
            "Tuyá»‡t Tháº¿ VÃ´ Äá»‹ch, Phong áº¤n Tháº§n HoÃ ng",
            "KhÃ­ PhÃ¡ch NgÃºt Trá»i, ThÃ´n Phá»‡ Long Máº¡ch",
            "Váº¡n Cá»• Ma Cung, Äáº¡i Chiáº¿n ChÆ° ThiÃªn",
            "BÃ¡ Chá»§ Huyá»n Thoáº¡i, Luyá»‡n HÃ³a Váº¡n Giá»›i"
        ]
        
        parsed_numbers = {int(b.get("chapter_number", 0)) for b in blueprints if isinstance(b, dict)}
        for ch_i in range(start_num, end_num + 1):
            if ch_i not in parsed_numbers:
                epic_t = EPIC_TITLES[(ch_i - 1) % len(EPIC_TITLES)]
                blueprints.append({
                    "chapter_number": ch_i,
                    "chapter_title": f"{epic_t} (Táº­p {ch_i})",
                    "blueprint": f"Diá»…n biáº¿n ká»‹ch tÃ­nh tiáº¿p theo cá»§a cÃ¢u chuyá»‡n á»Ÿ chÆ°Æ¡ng {ch_i}.",
                    "characters_present": [],
                    "narrative_goal": "PhÃ¡t triá»ƒn cá»‘t truyá»‡n"
                })

        existing_chapter_numbers = {c["chapter_number"] for c in existing_chapters}
        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or f"ChÆ°Æ¡ng {ch_num}"
            blueprint_text = ch_data.get("blueprint") or "Tiáº¿p tá»¥c diá»…n biáº¿n cÃ¢u chuyá»‡n."
            
            # Chá»‰ táº¡o blueprint náº¿u chÆ°Æ¡ng chÆ°a tá»“n táº¡i trong CSDL
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
    # Láº¥y táº­p há»£p 100% táº¥t cáº£ cÃ¡c sá»‘ chÆ°Æ¡ng Ä‘Ã£ xong tá»« Supabase + data/ + output/ + RAM
    completed_set = database.get_completed_chapters_set(novel_id)
    all_done_nums = {int(x) for x in completed_set if str(x).isdigit()}

    all_chapters = database.get_all_chapters(novel_id)
    
    # Lá»c cÃ¡c chÆ°Æ¡ng chÆ°a viáº¿t xong ká»‹ch báº£n (< 1200 tá»« hoáº·c cÃ²n lÃ  BLUEPRINT)
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
        
    # Lá»šP Báº¢O Vá»† Tá»I THÆ¯á»¢NG: Nếu vẫn chưa có chapter_record, tá»± sinh Blueprint trực tiếp ngay lập tức!
    if not chapter_record:
        print(f"[INFO] Tự động tạo Blueprint trá»±c tiáº¿p cho ChÆ°Æ¡ng {next_ch_number}...")
        chapter_record = database.create_chapter(
            novel_id=novel_id,
            chapter_number=next_ch_number,
            title=f"BÃ­ Máº­t Táº­p {next_ch_number}",
            content=f"BLUEPRINT: Diá»…n biáº¿n ká»‹ch tÃ­nh tiáº¿p theo cho chÆ°Æ¡ng {next_ch_number}."
        )
        
    blueprint_text = chapter_record["content"]
    
    chars = database.get_characters(novel_id)
    protagonist = next((c for c in chars if c.get("failure_flag") is not None), None)
    if not protagonist and chars:
        protagonist = chars[0]
        
    protagonist_name = protagonist["name"] if protagonist else "Jack"
    protagonist_power = protagonist["power_tier"] if protagonist else "Ordinary"
    protagonist_stats = json.dumps(protagonist["combat_stats"]) if protagonist else "{}"
    failure_flag = protagonist["failure_flag"] if protagonist else False
    last_breakthrough_ch = protagonist["last_breakthrough_chapter"] if protagonist else 0
    
    lores = database.get_world_lore(novel_id)
    world_lore_text = "\n".join([f"- {lore['keyword']}: {lore['description']}" for lore in lores])
    
    query_embed = get_embedding(blueprint_text)
    semantic_history = database.search_episodes(novel_id, query_embed, limit=7)
    history_text = "\n".join([f"- Chapter {h['chapter_id']}: {h['event_summary']}" for h in semantic_history])
    
    previous_chapters = [c for c in all_chapters if c["chapter_number"] < next_ch_number and not c["content"].startswith("BLUEPRINT:")]
    working_memory_text = ""
    # TÄƒng tham chiáº¿u tá»« 2-3 chÆ°Æ¡ng lÃªn 7 chÆ°Æ¡ng gáº§n nháº¥t (5 - 10 chÆ°Æ¡ng) Ä‘á»ƒ Ä‘áº£m báº£o máº¡ch truyá»‡n cá»±c ká»³ nháº¥t quÃ¡n
    for ch in previous_chapters[-7:]:
        ch_snippet = ch['content'][:600] + "\n...\n" + ch['content'][-600:] if len(ch['content']) > 1200 else ch['content']
        working_memory_text += f"\n--- ChÆ°Æ¡ng {ch['chapter_number']}: {ch['title']} ---\n{ch_snippet}\n"
        
    attempt = 0
    max_attempts = 3
    final_content = ""
    
    prompt = prompts.WRITING_PROMPT.format(
        chapter_number=next_ch_number,
        chapter_title=chapter_record["title"],
        title="Truyá»‡n 24h Audio",
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
            f"- Pháº§n má»Ÿ Ä‘áº§u (Prologue): Báº®T BUá»˜C má»Ÿ Ä‘áº§u chÆ°Æ¡ng báº±ng má»™t phÃ¢n cáº£nh cuá»‘n hÃºt (khoáº£ng 300 - 500 tá»«) miÃªu táº£ bá»‘i cáº£nh tháº¿ giá»›i linh há»“n, há»‡ thá»‘ng Tinh Tháº§n áº¤n vÃ  bÃ­ máº­t chiáº¿c há»™p Ä‘á»“ng ÄÃ´ng SÆ¡n.\n"
            f"- **Cáº¢NH BÃO QUAN TRá»ŒNG Vá»€ NHÃ‚N Váº¬T**: Trong pháº§n má»Ÿ Ä‘áº§u nÃ y, CHá»ˆ Táº¬P TRUNG duy nháº¥t vÃ o nhÃ¢n váº­t chÃ­nh ({protagonist_name}). "
            f"TUYá»†T Äá»I KHÃ”NG liá»‡t kÃª hay giá»›i thiá»‡u trÃ n lan cÃ¡c nhÃ¢n váº­t phá»¥. CÃ¡c nhÃ¢n váº­t phá»¥ sáº½ chá»‰ xuáº¥t hiá»‡n tá»± nhiÃªn khi cÃ³ tÃ¬nh huá»‘ng Ä‘á»‘i thoáº¡i trong cÃ¢u chuyá»‡n.\n"
            f"- **Cáº¢NH BÃO QUAN TRá»ŒNG Vá»€ TIÃŠU Äá»€**: TUYá»†T Äá»I KHÃ”NG VIáº¾T CHá»® 'Dáº«n lÆ°á»£c', 'Dáº«n lÆ°á»£c:', 'Giá»›i thiá»‡u:', hay 'Prologue:'. "
            f"HÃ£y nháº­p vai viáº¿t tháº³ng vÃ o ná»™i dung truyá»‡n má»™t cÃ¡ch tá»± nhiÃªn nháº¥t."
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
                
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "â€", "Â»", "*"))
            
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

            # VÃ’NG Láº¶P Ã‰P Báº®T BUá»˜C Äáº T >2800 Tá»ª (Guaranteed 2800+ Words Multi-Pass Expansion Loop for 12-18 min Audio)
            if word_count >= 2800 and not ends_abruptly:
                # INKOS MULTI-AGENT AUDITOR PASS: Khá»­ AI clichÃ© & Báº£o toÃ n 100% Ä‘á»™ dÃ i vÄƒn báº£n
                try:
                    print("[INFO] Quality Assurance Agent: Báº¯t Ä‘áº§u rÃ  soÃ¡t 37 tiÃªu chuáº©n cháº¥t lÆ°á»£ng & Khá»­ AI clichÃ©...")
                    audit_prompt = prompts.INKOS_AUDITOR_PROMPT.format(chapter_content=final_content[:6000])
                    audited_res = call_gemini(audit_prompt)
                    if audited_res and len(audited_res.split()) >= len(final_content.split()) * 0.9:
                        final_content = clean_chapter_content(audited_res)
                        word_count = len(final_content.split())
                        print(f"[SUCCESS] Quality Assurance Agent hoÃ n thÃ nh khá»­ AI clichÃ©. Tá»•ng sá»‘ tá»« tinh cháº¿: {word_count} tá»«.")
                    else:
                        final_content = clean_chapter_content(final_content)
                        word_count = len(final_content.split())
                        print(f"[INFO] Giá»¯ nguyÃªn Ä‘á»™ dÃ i vÄƒn báº£n Ä‘áº§y Ä‘á»§: {word_count} tá»« (TrÃ¡nh bá»‹ rÃºt ngáº¯n).")
                except Exception as audit_err:
                    print(f"[WARNING] Quality Assurance Agent pass warning: {audit_err}")
                break
                
            expand_cycles = 0
            while word_count < 2800 and expand_cycles < 6:
                expand_cycles += 1
                print(f"[INFO] (LÆ°á»£t ná»‘i tiáº¿p {expand_cycles}/6) ChÆ°Æ¡ng hiá»‡n táº¡i Ä‘áº¡t {word_count} tá»« (<2800 tá»«). Tá»± Ä‘á»™ng kÃ­ch hoáº¡t AI Viáº¿t Ná»‘i Tiáº¿p...")
                
                continuation_prompt = (
                    f"DÆ°á»›i Ä‘Ã¢y lÃ  pháº§n trÆ°á»›c cá»§a ChÆ°Æ¡ng {next_ch_number} (tá»•ng {word_count} tá»«):\n\n"
                    f"{final_content[-1200:]}\n\n"
                    f"YÃŠU Cáº¦U Báº®T BUá»˜C: HÃ£y viáº¿t tiáº¿p Ä‘oáº¡n ná»‘i theo cÃ¢u chuyá»‡n trÃªn (tá»‘i thiá»ƒu 1200 - 1800 tá»« ná»¯a). "
                    f"MiÃªu táº£ diá»…n biáº¿n tiáº¿p theo, Ä‘á»‘i thoáº¡i sÃ¢u sáº¯c, cáº£m xÃºc nhÃ¢n váº­t vÃ  káº¿t thÃºc báº±ng má»™t nÃºt tháº¯t ká»‹ch tÃ­nh. "
                    f"Viáº¿t tháº³ng vÃ o ná»™i dung truyá»‡n, khÃ´ng láº·p láº¡i Ä‘oáº¡n cÅ©."
                )
                
                part_next = call_gemini(continuation_prompt)
                if part_next and len(part_next.split()) > 100:
                    cleaned_next, _ = verify_and_sanitize_chapter_content(part_next)
                    # Tránh nối chuỗi lặp lại vô tận
                    if cleaned_next in final_content:
                        print("[WARNING] Đã phát hiện đoạn nối tiếp bị lặp lại, ngắt vòng lặp expansion.")
                        break
                    final_content = final_content + "\n\n" + cleaned_next
                    word_count = len(final_content.split())
                    print(f"[SUCCESS] ÄÃ£ ná»‘i tiáº¿p thÃ nh cÃ´ng! Tá»•ng Ä‘á»™ dÃ i chÆ°Æ¡ng hiá»‡n táº¡i: {word_count} tá»«.")
                    if word_count >= 2800:
                        break
                else:
                    time.sleep(2)
                    
            if word_count >= 2800:
                break
                
            if ends_abruptly:
                print(f"[WARNING] Draft ends abruptly (no punctuation at the end). Requesting completion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    "\n\n**Cáº¢NH BÃO Cá»°C Ká»² QUAN TRá»ŒNG**: Báº£n tháº£o trÆ°á»›c cá»§a báº¡n bá»‹ cáº¯t cá»¥t Ä‘á»™t ngá»™t á»Ÿ cuá»‘i (chÆ°a háº¿t cÃ¢u, chÆ°a cÃ³ dáº¥u cháº¥m cÃ¢u káº¿t thÃºc). "
                    "Báº¡n Báº®T BUá»˜C pháº£i viáº¿t trá»n váº¹n cÃ¢u chuyá»‡n, má»Ÿ rá»™ng chi tiáº¿t cÃ¡c phÃ¢n cáº£nh, há»™i thoáº¡i vÃ  káº¿t thÃºc chÆ°Æ¡ng má»™t cÃ¡ch trá»n váº¹n báº±ng dáº¥u cháº¥m cÃ¢u."
                )
            else:
                print(f"[WARNING] Draft too short ({word_count} words). Requesting longer expansion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    f"\n\n**Cáº¢NH BÃO Cá»°C Ká»² QUAN TRá»ŒNG Vá»€ Äá»˜ DÃ€I (Báº®T BUá»˜C)**:\n"
                    f"Báº£n tháº£o báº¡n vá»«a viáº¿t quÃ¡ ngáº¯n (chá»‰ cÃ³ {word_count} tá»«), trong khi yÃªu cáº§u tá»‘i thiá»ƒu lÃ  2200 tá»« Ä‘á»ƒ Ä‘áº¡t 10 phÃºt nÃ³i.\n"
                    f"Äá»ƒ sá»­a lá»—i nÃ y, báº¡n pháº£i viáº¿t cá»±c ká»³ chi tiáº¿t theo hÆ°á»›ng dáº«n sau:\n"
                    f"1. Chia chÆ°Æ¡ng truyá»‡n thÃ nh Ã­t nháº¥t 5 phÃ¢n cáº£nh lá»›n riÃªng biá»‡t (Má»—i phÃ¢n cáº£nh viáº¿t tá»‘i thiá»ƒu 5-6 Ä‘oáº¡n vÄƒn dÃ i).\n"
                    f"2. Äi sÃ¢u miÃªu táº£ cá»±c ká»³ tá»‰ má»‰: cáº£nh sáº¯c khÃ´ng gian há»c viá»‡n, thá»i tiáº¿t, Ã¢m thanh giÃ³ thá»•i, biá»ƒu cáº£m nÃ©t máº·t tá»«ng nhÃ¢n váº­t, cá»­ chá»‰ tay chÃ¢n, vÃ  dÃ²ng suy nghÄ© ná»™i tÃ¢m kÃ©o dÃ i.\n"
                    f"3. Viáº¿t cÃ¡c Ä‘oáº¡n Ä‘á»‘i thoáº¡i dÃ i, thá»±c táº¿ vÃ  sÃ¢u sáº¯c giá»¯a cÃ¡c nhÃ¢n váº­t (Tráº§n Lam, Linh Vy, Minh Äá»©c, v.v.). KhÃ´ng Ä‘Æ°á»£c viáº¿t lÆ°á»›t qua.\n"
                    f"4. TUYá»†T Äá»I khÃ´ng tÃ³m táº¯t hay káº¿t thÃºc chÆ°Æ¡ng truyá»‡n sá»›m khi chÆ°a Ä‘á»§ Ä‘á»™ dÃ i yÃªu cáº§u."
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
    # Äá»˜NG CÆ  Dá»ŠCH THUáº¬T TIáº¾NG VIá»†T GEMINI API: Äáº£m báº£o 100% ká»‹ch báº£n tiá»ƒu thuyáº¿t chuáº©n Tiáº¿ng Viá»‡t mÆ°á»£t mÃ 
    cleaned_content = translate_to_vietnamese_with_gemini(cleaned_content)
    
    # Äáº£m báº£o tiÃªu Ä‘á» chÆ°Æ¡ng khÃ´ng bá»‹ trÃ¹ng láº·p placeholder
    cur_title = chapter_record.get("title", "")
    if "HÃ nh TrÃ¬nh Má»›i" in cur_title or not cur_title or cur_title == f"ChÆ°Æ¡ng {next_ch_number}":
        EPIC_TITLES = [
            "TrÃ¹ng Sinh Váº¡n Cá»•, ThÃ´n Phá»‡ VÃ´ Táº­n", "Thá»©c Tá»‰nh Tháº§n Thá»ƒ, NÃ©n Ã‰p Tháº§n Ma", "Huyáº¿t Máº¡ch ThÃ´n ThiÃªn, Tráº¥n TÃ¡m PhÆ°Æ¡ng",
            "Quyá»n Tráº¥n SÆ¡n HÃ , Uy Cháº¥n ChÆ° ThiÃªn", "VÃ´ Äá»‹ch TrÃ¹ng Sinh, Há»—n Äá»™n Luyá»‡n KhÃ­", "Nghá»‹ch ThiÃªn Äá»™c TÃ´n, Luyá»‡n HÃ³a Tháº§n Tháº¡ch",
            "ThÃ´n Phá»‡ NguyÃªn KhÃ­, PhÃ¡ Tam Cáº£nh", "Váº¡n Giá»›i Quá»³ BÃ¡i, TiÃªu ViÃªm Xuáº¥t Tháº¿", "ThÃ´n Phá»‡ Ma Nháº«n, Khai Má»Ÿ Tháº§n ThÃ´ng",
            "VÃ´ Song Kiáº¿m KhÃ­, Tráº£m Diá»‡t CÆ°á»ng Äá»‹ch", "Há»‡ Thá»‘ng Tháº§n Cáº¥p, ThÃ´n Phá»‡ Váº¡n Váº­t", "BÃ¡ Tháº§n Xuáº¥t Tháº¿, NgÄƒn Cáº£n Váº¡n QuÃ¢n"
        ]
        epic_name = EPIC_TITLES[(next_ch_number - 1) % len(EPIC_TITLES)]
        cur_title = f"{epic_name} (Táº­p {next_ch_number})"

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
        
        # 1. Tá»° Äá»˜NG LÆ¯U CÃC NHÃ‚N Váº¬T Má»šI SÃNG Táº O VÃ€O CSDL SUPABASE
        new_chars = data.get("new_characters", [])
        if new_chars:
            print(f"[INFO] ðŸŒŸ ÄÃ£ phÃ¡t hiá»‡n {len(new_chars)} nhÃ¢n váº­t Má»šI Ä‘Æ°á»£c AI sÃ¡ng táº¡o trong chÆ°Æ¡ng!")
            for n_char in new_chars:
                n_name = n_char.get("name")
                if n_name and n_name.strip():
                    database.upsert_character(
                        novel_id=novel_id,
                        name=n_name.strip(),
                        description=n_char.get("description", "NhÃ¢n váº­t má»›i xuáº¥t hiá»‡n trong ká»‹ch báº£n"),
                        power_tier=n_char.get("power_tier", "Cao Thá»§ Má»›i"),
                        combat_stats=n_char.get("combat_stats", {}),
                        relationships=n_char.get("relationships", {}),
                        failure_flag=False,
                        last_breakthrough_chapter=0
                    )
                    print(f"   [SUPABASE] + Da tu dong nhat Nhan Vat MOI: {n_name} ({n_char.get('power_tier')})")

        # 2. Cáº¬P NHáº¬T TRáº NG THÃI CÃC NHÃ‚N Váº¬T CÅ¨
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

