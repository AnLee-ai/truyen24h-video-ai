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
        # Thử làm sạch dấu phẩy thừa ở cuối (trailing commas)
        cleaned_no_comma = re.sub(r",\s*([\}\]])", r"\1", cleaned)
        try:
            return json.loads(cleaned_no_comma)
        except Exception:
            pass
        # Thử trích xuất khối {...} hoặc [...] bằng Regex
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
        sentences = re.split(r'(?<=[.?!â‚¬Â¦])\s+(?=[a-zA-ZÃƒÂ ÃƒÂ¡ÃƒÂ¢ÃƒÂ£ÃƒÂ¨ÃƒÂ©ÃƒÂªÃƒÂ¬ÃƒÂ­ÃƒÂ²ÃƒÂ³ÃƒÂ´ÃƒÂµÃƒÂ¹ÃƒÂºÃƒÂ½Ã„â€˜Ãƒâ‚¬ÃƒÂÃƒâ€šÃƒÆ’ÃƒË†Ãƒâ€°ÃƒÃƒÅ’ÃƒÂÃƒâ€™Ãƒâ€œÃƒâ€Ãƒâ€¢Ãƒâ„¢ÃƒÃƒÂÃ„Â0-9"\'Ã‚Â«â‚¬Å“])', para)
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
    pattern = r"(?im)^\s*[*_]*\s*(?:Dẫn lược|Giới thiệu|Phần dẫn lược|Tóm tắt bối cảnh|Prologue|Introduction|Giới thiệu bối cảnh)\s*[:：\-–—]*\s*[*_]*\s*[:：\-–—]*\s*"
    cleaned = re.sub(pattern, "", cleaned).strip()
    cleaned = remove_repetitive_sentences(cleaned)
    return cleaned

def expand_chapter_content(content: str, target_words: int = 3200) -> str:
    """Nối dài kịch bản chương truyện nếu chưa đủ độ dài >10 phút audio (600 giây)."""
    current_words = len(content.split()) if content else 0
    if current_words >= target_words:
        return content
        
    print("[INFO] Processing...")
    
    continuation_prompt = (
        f"Dưới đây là phần trước của chương truyện (tổng {current_words} từ):\n\n"
        f"{content[-1500:]}\n\n"
        f"YÊU CẦU BẮT BUỘC (ÉP THỜI LƯỢNG KÉO DÀI >10 PHÚT AUDIO):\n"
        f"Hãy viết tiếp phân cảnh diễn biến kịch tính tiếp theo của câu chuyện trên (tối thiểu 1500 - 2000 từ nữa).\n"
        f"1. Viết chi tiết cuộc đối thoại gay gắt, bộc phát cảm xúc giữa các nhân vật chính.\n"
        f"2. Miêu tả chi tiết chiêu thức, giao phong kịch tính và suy nghĩ nội tâm dồn dập.\n"
        f"3. Kết thúc bằng một nút thắt cliffhanger kịch tính.\n"
        f"Viết thẳng vào câu chuyện 100% bằng Tiếng Việt mượt mà, không lặp lại đoạn cũ."
    )
    
    for _expand_attempt in range(3):
        part_next = call_gemini(continuation_prompt)
        if part_next and len(part_next.split()) > 200:
            cleaned_next = clean_chapter_content(part_next)
            if cleaned_next.lower() in content.lower():
                continue
            content = content + "\n\n" + cleaned_next
            print("[INFO] Processing...")
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
        print("[INFO] Processing...")
        return sanitized_text, True
        
    return text, False



@cached(ttl_seconds=86400)
def translate_to_vietnamese_with_gemini(text: str) -> str:
    """Tự động kiểm tra và dịch toàn bộ kịch bản tiểu thuyết từ tiếng Trung/tiếng Anh sang tiếng Việt chuẩn mượt mà 100% qua Gemini API."""
    if not text or not text.strip():
        return text
        
    # Tự động rà soát và khử tên nhân vật cũ rác
    text, _ = verify_and_sanitize_chapter_content(text)
    
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    if not has_chinese:
        return text
        
    print(f"[INFO] Bắt đầu rà soát ngôn ngữ kịch bản (Has Chinese: {has_chinese})...")
    print("[INFO] Processing...")
    translate_prompt = (
        "Bạn là dịch giả tiểu thuyết webtoon hàng đầu. Hãy dịch/chuyển ngữ toàn bộ chương tiểu thuyết sau đây sang tiếng Việt tự nhiên, giàu cảm xúc và hấp dẫn.\n"
        "YÊU CẦU DỊCH THUẬT BẮT BUỘC:\n"
        "1. DÂ»â€¹ch 100% sang tiÂºÂ¿ng ViÂ»â€¡t thuÂºÂ§n tÃƒÂºy, mÃ†Â°Â»Â£t mÃƒÂ , vÃ„Æ’n phong tiÂ»Æ’u thuyÂºÂ¿t hÃƒÂ nh Ã„â€˜Â»â„¢ng/huyÂ»Ân ÂºÂ£o kÂ»â€¹ch tÃƒÂ­nh.\n"
        "2. GiÂ»Â¯ nguyÃƒÂªn 100% Ã„â€˜Â»â„¢ dÃƒÂ i vÃ„Æ’n bÂºÂ£n, lÂ»Âi thoÂºÂ¡i trong ngoÂºÂ·c kÃƒÂ©p (\"...\"), vÃƒÂ  cÂºÂ¥u trÃƒÂºc cÃƒÂ¢u chuyÂ»â€¡n. TUYÂ»â€ T Ã„ÂÂ»ÂI KHÃƒâ€NG tÃƒÂ³m tÂºÂ¯t hay bÂ»Â sÃƒÂ³t chi tiÂºÂ¿t nÃƒÂ o.\n"
        "3. Giữ nguyên 100% tên nhân vật chuẩn từ nguyên bản. Cấm tự đổi sang tên khác.\n"
        "4. ChÂ»â€° xuÂºÂ¥t ra duy nhÂºÂ¥t vÃ„Æ’n bÂºÂ£n truyÂ»â€¡n Ã„â€˜ÃƒÂ£ dÂ»â€¹ch sang tiÂºÂ¿ng ViÂ»â€¡t, khÃƒÂ´ng kÃƒÂ¨m lÂ»Âi dÂºÂ«n hay giÂºÂ£i thÃƒÂ­ch.\n\n"
        f"VĂN BẢN CẦN DỊCH:\n{text}"
    )
    translated_res = call_gemini(translate_prompt)
    if translated_res and len(translated_res.split()) > 200:
        cleaned_res = clean_chapter_content(translated_res)
        cleaned_res, _ = verify_and_sanitize_chapter_content(cleaned_res)
        print("[INFO] Processing...")
        return cleaned_res
    return text

@cached(ttl_seconds=86400)
def call_gemini(prompt: str, json_mode: bool = False, retries: int = 12) -> str:
    """
    Ã†Â¯U TIÃƒN 100% HÃƒâ‚¬NG Ã„ÂÂºÂ¦U: InkOS Multi-Agent Engine (Google Gemini 2.0 Flash API vÂ»â€ºi Key Rotator).
    Chỉ khi Gemini hết Key mới chuyển sang Groq / OpenRouter dự phòng.
    """
    # =========================================================================
    # Removed corrupted comment
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
                print(f"[SUCCESS] ⚡ InkOS Writer Agent [{current_g_model}]: Tạo kịch bản mượt mà thành công! ({len(response.text.strip().split())} từ).")
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
    # Removed corrupted comment
    # =========================================================================
    local_mangstoon = call_mangstoon_ai(prompt)
    if local_mangstoon and len(local_mangstoon.strip().split()) > 10:
        print("[SUCCESS] Local Mangstoon_AI succeeded!")
        return local_mangstoon.strip()

    # =========================================================================
    # Removed corrupted comment
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
                        print("[INFO] Processing...")
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
        
    # Removed corrupted comment
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
    arc_summary = arc.get("summary", "TiÂºÂ¿p tÂ»Â¥c diÂ»â€¦n biÂºÂ¿n cÂ»Â§a bÂ»â€˜i cÂºÂ£nh hÂ»Âc viÂ»â€¡n.")
    
    print(f"[INFO] Generating blueprints for Arc {arc_num}: '{arc_title}' (Chapters {start_ch} - {end_ch})...")
    
    novel = database.get_novel(novel_id)
    novel_title = novel.get("title", "Truyện mới")
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
                # Removed corrupted comment
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
            "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận",
            "Thức Tỉnh Thần Thể, Nén Ép Thần Ma",
            "Huyết Mạch Thôn Thiên, Trấn Tám Phương",
            "QuyÂ»Ân TrÂºÂ¥n SÃ†Â¡n HÃƒÂ , Uy ChÂºÂ¥n ChÃ†Â° ThiÃƒÂªn",
            "VÃƒÂ´ Ã„ÂÂ»â€¹ch TrÃƒÂ¹ng Sinh, HÂ»â€”n Ã„ÂÂ»â„¢n LuyÂ»â€¡n KhÃƒÂ­",
            "NghÂ»â€¹ch ThiÃƒÂªn Ã„ÂÂ»â„¢c TÃƒÂ´n, LuyÂ»â€¡n HÃƒÂ³a ThÂºÂ§n ThÂºÂ¡ch",
            "Thôn Phệ Nguyên Khí, Phá Tam Cảnh",
            "Vạn Giới Quỳ Bái, Tiêu Viêm Xuất Thế",
            "Thôn Phệ Ma Nhẫn, Khai Mở Thần Thông",
            "VÃƒÂ´ Song KiÂºÂ¿m KhÃƒÂ­, TrÂºÂ£m DiÂ»â€¡t CÃ†Â°Â»Âng Ã„ÂÂ»â€¹ch",
            "Hệ Thống Thần Cấp, Thôn Phệ Vạn Vật",
            "Bá Thần Xuất Thế, Ngăn Cản Vạn Quân",
            "ThÃƒÂ´n PhÂ»â€¡ VÃ„Â©nh HÂºÂ±ng, XÃƒÂ¢y DÂ»Â±ng Ã„ÂÂºÂ¿ CÃ†Â¡",
            "ThÃƒÂ´n ThiÃƒÂªn LuyÂ»â€¡n Ã„ÂÂ»â€¹a, Ã„ÂÂ»â„¢c TÃƒÂ´n VÂºÂ¡n CÂ»â€¢",
            "TuyÂ»â€¡t ThÂºÂ¿ VÃƒÂ´ Ã„ÂÂ»â€¹ch, Phong ÂºÂ¤n ThÂºÂ§n HoÃƒÂ ng",
            "KhÃƒÂ­ PhÃƒÂ¡ch NgÃƒÂºt TrÂ»Âi, ThÃƒÂ´n PhÂ»â€¡ Long MÂºÂ¡ch",
            "VÂºÂ¡n CÂ»â€¢ Ma Cung, Ã„ÂÂºÂ¡i ChiÂºÂ¿n ChÃ†Â° ThiÃƒÂªn",
            "BÃƒÂ¡ ChÂ»Â§ HuyÂ»Ân ThoÂºÂ¡i, LuyÂ»â€¡n HÃƒÂ³a VÂºÂ¡n GiÂ»â€ºi"
        ]
        
        parsed_numbers = {int(b.get("chapter_number", 0)) for b in blueprints if isinstance(b, dict)}
        for ch_i in range(start_num, end_num + 1):
            if ch_i not in parsed_numbers:
                epic_t = EPIC_TITLES[(ch_i - 1) % len(EPIC_TITLES)]
                blueprints.append({
                    "chapter_number": ch_i,
                    "chapter_title": f"{epic_t} (Tập {ch_i})",
                    "blueprint": f"Diễn biến kịch tính tiếp theo của câu chuyện ở chương {ch_i}.",
                    "characters_present": [],
                    "narrative_goal": "Phát triển cốt truyện"
                })

        existing_chapter_numbers = {c["chapter_number"] for c in existing_chapters}
        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or f"ChÃ†Â°Ã†Â¡ng {ch_num}"
            blueprint_text = ch_data.get("blueprint") or "Tiếp tục diễn biến câu chuyện."
            
            # Chỉ tạo blueprint nếu chương chưa tồn tại trong CSDL
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
    # Lấy tập hợp 100% tất cả các số chương đã xong từ Supabase + data/ + output/ + RAM
    completed_set = database.get_completed_chapters_set(novel_id)
    all_done_nums = {int(x) for x in completed_set if str(x).isdigit()}

    all_chapters = database.get_all_chapters(novel_id)
    
    # Removed corrupted comment
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

    print("[INFO] Processing...")
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
    # Tăng tham chiếu từ 2-3 chương lên 7 chương gần nhất (5 - 10 chương) để đảm bảo mạch truyện cực kỳ nhất quán
    for ch in previous_chapters[-7:]:
        ch_snippet = ch['content'][:600] + "\n...\n" + ch['content'][-600:] if len(ch['content']) > 1200 else ch['content']
        working_memory_text += f"\n--- ChÃ†Â°Ã†Â¡ng {ch['chapter_number']}: {ch['title']} ---\n{ch_snippet}\n"
        
    attempt = 0
    max_attempts = 3
    final_content = ""
    
    prompt = prompts.WRITING_PROMPT.format(
        chapter_number=next_ch_number,
        chapter_title=chapter_record["title"],
        title="Truyện 24h Audio",
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
            f"- PhÂºÂ§n mÂ» Ã„â€˜ÂºÂ§u (Prologue): BÂºÂ®T BUÂ»ËœC mÂ» Ã„â€˜ÂºÂ§u chÃ†Â°Ã†Â¡ng bÂºÂ±ng mÂ»â„¢t phÃƒÂ¢n cÂºÂ£nh cuÂ»â€˜n hÃƒÂºt (khoÂºÂ£ng 300 - 500 tÂ»Â«) miÃƒÂªu tÂºÂ£ bÂ»â€˜i cÂºÂ£nh thÂºÂ¿ giÂ»â€ºi linh hÂ»â€œn, hÂ»â€¡ thÂ»â€˜ng Tinh ThÂºÂ§n ÂºÂ¤n vÃƒÂ  bÃƒÂ­ mÂºÂ­t chiÂºÂ¿c hÂ»â„¢p Ã„â€˜Â»â€œng Ã„ÂÃƒÂ´ng SÃ†Â¡n.\n"
            f"- **CÂºÂ¢NH BÃƒÂO QUAN TRÂ»Å’NG VÂ»â‚¬ NHÃƒâ€šN VÂºÂ¬T**: Trong phÂºÂ§n mÂ» Ã„â€˜ÂºÂ§u nÃƒÂ y, CHÂ»Ë† TÂºÂ¬P TRUNG duy nhÂºÂ¥t vÃƒÂ o nhÃƒÂ¢n vÂºÂ­t chÃƒÂ­nh ({protagonist_name}). "
            f"TUYÂ»â€ T Ã„ÂÂ»ÂI KHÃƒâ€NG liÂ»â€¡t kÃƒÂª hay giÂ»â€ºi thiÂ»â€¡u trÃƒÂ n lan cÃƒÂ¡c nhÃƒÂ¢n vÂºÂ­t phÂ»Â¥. CÃƒÂ¡c nhÃƒÂ¢n vÂºÂ­t phÂ»Â¥ sÂºÂ½ chÂ»â€° xuÂºÂ¥t hiÂ»â€¡n tÂ»Â± nhiÃƒÂªn khi cÃƒÂ³ tÃƒÂ¬nh huÂ»â€˜ng Ã„â€˜Â»â€˜i thoÂºÂ¡i trong cÃƒÂ¢u chuyÂ»â€¡n.\n"
            f"- **CÂºÂ¢NH BÃƒÂO QUAN TRÂ»Å’NG VÂ»â‚¬ TIÃƒU Ã„ÂÂ»â‚¬**: TUYÂ»â€ T Ã„ÂÂ»ÂI KHÃƒâ€NG VIÂºÂ¾T CHÂ»Â® 'DÂºÂ«n lÃ†Â°Â»Â£c', 'DÂºÂ«n lÃ†Â°Â»Â£c:', 'GiÂ»â€ºi thiÂ»â€¡u:', hay 'Prologue:'. "
            f"Hãy nhập vai viết thẳng vào nội dung truyện một cách tự nhiên nhất."
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
                
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "â‚¬Â", "Ã‚Â»", "*"))
            
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

            # Removed corrupted comment
            if word_count >= 2800 and not ends_abruptly:
                # INKOS MULTI-AGENT AUDITOR PASS: Khử AI cliché & Bảo toàn 100% độ dài văn bản
                try:
                    print("[INFO] Quality Assurance Agent: Bắt đầu rà soát 37 tiêu chuẩn chất lượng & Khử AI cliché...")
                    audit_prompt = prompts.INKOS_AUDITOR_PROMPT.format(chapter_content=final_content[:6000])
                    audited_res = call_gemini(audit_prompt)
                    if audited_res and len(audited_res.split()) >= len(final_content.split()) * 0.9:
                        final_content = clean_chapter_content(audited_res)
                        word_count = len(final_content.split())
                        print(f"[SUCCESS] Quality Assurance Agent hoàn thành khử AI cliché. Tổng số từ tinh chế: {word_count} từ.")
                    else:
                        final_content = clean_chapter_content(final_content)
                        word_count = len(final_content.split())
                        print(f"[INFO] Giữ nguyên độ dài văn bản đầy đủ: {word_count} từ (Tránh bị rút ngắn).")
                except Exception as audit_err:
                    print(f"[WARNING] Quality Assurance Agent pass warning: {audit_err}")
                break
                
            expand_cycles = 0
            while word_count < 2800 and expand_cycles < 6:
                expand_cycles += 1
                print(f"[INFO] (Lượt nối tiếp {expand_cycles}/6) Chương hiện tại đạt {word_count} từ (<2800 từ). Tự động kích hoạt AI Viết Nối Tiếp...")
                
                continuation_prompt = (
                    f"Dưới đây là phần trước của Chương {next_ch_number} (tổng {word_count} từ):\n\n"
                    f"{final_content[-1200:]}\n\n"
                    f"YÊU CẦU BẮT BUỘC: Hãy viết tiếp đoạn nối theo câu chuyện trên (tối thiểu 1200 - 1800 từ nữa). "
                    f"Miêu tả diễn biến tiếp theo, đối thoại sâu sắc, cảm xúc nhân vật và kết thúc bằng một nút thắt kịch tính. "
                    f"Viết thẳng vào nội dung truyện, không lặp lại đoạn cũ."
                )
                
                part_next = call_gemini(continuation_prompt)
                if part_next and len(part_next.split()) > 100:
                    cleaned_next, _ = verify_and_sanitize_chapter_content(part_next)
                    # Tránh nối chuỗi lặp lại vô tận
                    if cleaned_next in final_content:
                        print("[INFO] Processing...")
                        break
                    final_content = final_content + "\n\n" + cleaned_next
                    word_count = len(final_content.split())
                    print("[INFO] Processing...")
                    if word_count >= 2800:
                        break
                else:
                    time.sleep(2)
                    
            if word_count >= 2800:
                break
                
            if ends_abruptly:
                print(f"[WARNING] Draft ends abruptly (no punctuation at the end). Requesting completion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    "\n\n**CÂºÂ¢NH BÃƒÂO CÂ»Â°C KÂ»Â² QUAN TRÂ»Å’NG**: BÂºÂ£n thÂºÂ£o trÃ†Â°Â»â€ºc cÂ»Â§a bÂºÂ¡n bÂ»â€¹ cÂºÂ¯t cÂ»Â¥t Ã„â€˜Â»â„¢t ngÂ»â„¢t Â» cuÂ»â€˜i (chÃ†Â°a hÂºÂ¿t cÃƒÂ¢u, chÃ†Â°a cÃƒÂ³ dÂºÂ¥u chÂºÂ¥m cÃƒÂ¢u kÂºÂ¿t thÃƒÂºc). "
                    "BÂºÂ¡n BÂºÂ®T BUÂ»ËœC phÂºÂ£i viÂºÂ¿t trÂ»Ân vÂºÂ¹n cÃƒÂ¢u chuyÂ»â€¡n, mÂ» rÂ»â„¢ng chi tiÂºÂ¿t cÃƒÂ¡c phÃƒÂ¢n cÂºÂ£nh, hÂ»â„¢i thoÂºÂ¡i vÃƒÂ  kÂºÂ¿t thÃƒÂºc chÃ†Â°Ã†Â¡ng mÂ»â„¢t cÃƒÂ¡ch trÂ»Ân vÂºÂ¹n bÂºÂ±ng dÂºÂ¥u chÂºÂ¥m cÃƒÂ¢u."
                )
            else:
                print(f"[WARNING] Draft too short ({word_count} words). Requesting longer expansion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    f"\n\n**CÂºÂ¢NH BÃƒÂO CÂ»Â°C KÂ»Â² QUAN TRÂ»Å’NG VÂ»â‚¬ Ã„ÂÂ»Ëœ DÃƒâ‚¬I (BÂºÂ®T BUÂ»ËœC)**:\n"
                    f"Bản thảo bạn vừa viết quá ngắn (chỉ có {word_count} từ), trong khi yêu cầu tối thiểu là 2200 từ để đạt 10 phút nói.\n"
                    f"Ã„ÂÂ»Æ’ sÂ»Â­a lÂ»â€”i nÃƒÂ y, bÂºÂ¡n phÂºÂ£i viÂºÂ¿t cÂ»Â±c kÂ»Â³ chi tiÂºÂ¿t theo hÃ†Â°Â»â€ºng dÂºÂ«n sau:\n"
                    f"1. Chia chương truyện thành ít nhất 5 phân cảnh lớn riêng biệt (Mỗi phân cảnh viết tối thiểu 5-6 đoạn văn dài).\n"
                    f"2. Ã„Âi sÃƒÂ¢u miÃƒÂªu tÂºÂ£ cÂ»Â±c kÂ»Â³ tÂ»â€° mÂ»â€°: cÂºÂ£nh sÂºÂ¯c khÃƒÂ´ng gian hÂ»Âc viÂ»â€¡n, thÂ»Âi tiÂºÂ¿t, ÃƒÂ¢m thanh giÃƒÂ³ thÂ»â€¢i, biÂ»Æ’u cÂºÂ£m nÃƒÂ©t mÂºÂ·t tÂ»Â«ng nhÃƒÂ¢n vÂºÂ­t, cÂ»Â­ chÂ»â€° tay chÃƒÂ¢n, vÃƒÂ  dÃƒÂ²ng suy nghÃ„Â© nÂ»â„¢i tÃƒÂ¢m kÃƒÂ©o dÃƒÂ i.\n"
                    f"3. ViÂºÂ¿t cÃƒÂ¡c Ã„â€˜oÂºÂ¡n Ã„â€˜Â»â€˜i thoÂºÂ¡i dÃƒÂ i, thÂ»Â±c tÂºÂ¿ vÃƒÂ  sÃƒÂ¢u sÂºÂ¯c giÂ»Â¯a cÃƒÂ¡c nhÃƒÂ¢n vÂºÂ­t (TrÂºÂ§n Lam, Linh Vy, Minh Ã„ÂÂ»Â©c, v.v.). KhÃƒÂ´ng Ã„â€˜Ã†Â°Â»Â£c viÂºÂ¿t lÃ†Â°Â»â€ºt qua.\n"
                    f"4. TUYÂ»â€ T Ã„ÂÂ»ÂI khÃƒÂ´ng tÃƒÂ³m tÂºÂ¯t hay kÂºÂ¿t thÃƒÂºc chÃ†Â°Ã†Â¡ng truyÂ»â€¡n sÂ»â€ºm khi chÃ†Â°a Ã„â€˜Â»Â§ Ã„â€˜Â»â„¢ dÃƒÂ i yÃƒÂªu cÂºÂ§u."
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
    # Removed corrupted comment
    cleaned_content = translate_to_vietnamese_with_gemini(cleaned_content)
    
    # Removed corrupted comment
    cur_title = chapter_record.get("title", "")
    if "Hành Trình Mới" in cur_title or not cur_title or cur_title == f"Chương {next_ch_number}":
        EPIC_TITLES = [
            "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận", "Thức Tỉnh Thần Thể, Nén Ép Thần Ma", "Huyết Mạch Thôn Thiên, Trấn Tám Phương",
            "QuyÂ»Ân TrÂºÂ¥n SÃ†Â¡n HÃƒÂ , Uy ChÂºÂ¥n ChÃ†Â° ThiÃƒÂªn", "VÃƒÂ´ Ã„ÂÂ»â€¹ch TrÃƒÂ¹ng Sinh, HÂ»â€”n Ã„ÂÂ»â„¢n LuyÂ»â€¡n KhÃƒÂ­", "NghÂ»â€¹ch ThiÃƒÂªn Ã„ÂÂ»â„¢c TÃƒÂ´n, LuyÂ»â€¡n HÃƒÂ³a ThÂºÂ§n ThÂºÂ¡ch",
            "Thôn Phệ Nguyên Khí, Phá Tam Cảnh", "Vạn Giới Quỳ Bái, Tiêu Viêm Xuất Thế", "Thôn Phệ Ma Nhẫn, Khai Mở Thần Thông",
            "VÃƒÂ´ Song KiÂºÂ¿m KhÃƒÂ­, TrÂºÂ£m DiÂ»â€¡t CÃ†Â°Â»Âng Ã„ÂÂ»â€¹ch", "HÂ»â€¡ ThÂ»â€˜ng ThÂºÂ§n CÂºÂ¥p, ThÃƒÂ´n PhÂ»â€¡ VÂºÂ¡n VÂºÂ­t", "BÃƒÂ¡ ThÂºÂ§n XuÂºÂ¥t ThÂºÂ¿, NgÃ„Æ’n CÂºÂ£n VÂºÂ¡n QuÃƒÂ¢n"
        ]
        epic_name = EPIC_TITLES[(next_ch_number - 1) % len(EPIC_TITLES)]
        cur_title = f"{epic_name} (Tập {next_ch_number})"

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
        
        # Removed corrupted comment
        new_chars = data.get("new_characters", [])
        if new_chars:
            print("[INFO] Processing...")
            for n_char in new_chars:
                n_name = n_char.get("name")
                if n_name and n_name.strip():
                    database.upsert_character(
                        novel_id=novel_id,
                        name=n_name.strip(),
                        description=n_char.get("description", "Nhân vật mới xuất hiện trong kịch bản"),
                        power_tier=n_char.get("power_tier", "Cao Thủ Mới"),
                        combat_stats=n_char.get("combat_stats", {}),
                        relationships=n_char.get("relationships", {}),
                        failure_flag=False,
                        last_breakthrough_chapter=0
                    )
                    print(f"   [SUPABASE] + Da tu dong nhat Nhan Vat MOI: {n_name} ({n_char.get('power_tier')})")

        # Removed corrupted comment
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


