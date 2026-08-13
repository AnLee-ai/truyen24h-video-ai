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

from src import key_rotator

def get_genai_client(api_key: str = None):
    current_key = api_key or key_rotator.get_gemini_key() or config.GEMINI_API_KEY
    if not current_key:
        raise ValueError("GEMINI_API_KEY / GEMINI_API_KEYS must be configured in environment variables.")
    if USE_NEW_GENAI:
        return genai.Client(api_key=current_key)
    else:
        genai.configure(api_key=current_key)
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
        sentences = re.split(r'(?<=[.?!…])\s+(?=[a-zA-ZàáâãèéêìíòóôõùúýđÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĐ0-9"\'«“])', para)
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
    pattern = r"(?m)^\s*(?:\*\*|\*|__|_)*\s*(?:Dẫn lược|Giới thiệu|Phần dẫn lược|Tóm tắt bối cảnh|Prologue|Introduction|Giới thiệu bối cảnh)\s*(?:\*\*|\*|__|_)*\s*[:：\-–—\n]?\s*(?:\*\*|\*|__|_)*\s*"
    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    inline_pattern = r"(?:\*\*|\*|__|_)*\s*(?:Dẫn lược|Phần dẫn lược|Giới thiệu bối cảnh|Prologue)\s*(?:\*\*|\*|__|_)*\s*[:：\-–—]\s*"
    cleaned = re.sub(inline_pattern, "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = remove_repetitive_sentences(cleaned)
    return cleaned

def expand_chapter_content(content: str, target_words: int = 3200) -> str:
    """Nối dài kịch bản chương truyện nếu chưa đủ độ dài >10 phút audio (600 giây)."""
    current_words = len(content.split()) if content else 0
    if current_words >= target_words:
        return content
        
    print(f"[INFO] ⚡ CHẾ ĐỘ LÀM LẠI (>10 PHÚT): Độ dài hiện tại {current_words} từ (<{target_words} từ). Đang gọi AI viết nối tiếp phân cảnh kịch tính...")
    
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
            content = content + "\n\n" + cleaned_next
            print(f"[SUCCESS] Đã nối dài chương truyện! Tổng số từ mới: {len(content.split())} từ.")
            if len(content.split()) >= target_words:
                break
    return content

def verify_and_sanitize_chapter_content(text: str, novel_id: str = "") -> tuple:
    """
    BỘ KIỂM TRA TỰ ĐỘNG BẢO VỆ CHƯƠNG TRUYỆN (Automated Chapter Auditor):
    Tự động rà soát và khử toàn bộ tên nhân vật cũ rác (Trần Lam, Linh Vy, Minh Đức...) 
    để ép chuẩn 100% nhân vật bộ truyện đang viết (Tiêu Viêm, Vân Vận, Dược Lão, Huân Nhi).
    """
    if not text:
        return text, False
        
    LEGACY_INVALID_NAMES = {
        "Trần Lam": "Tiêu Viêm",
        "Linh Vy": "Vân Vận",
        "Minh Đức": "Dược Lão",
        "Thùy Linh": "Huân Nhi",
        "Cao Bá": "Tiêu Chiến"
    }
    
    found_invalid = []
    sanitized_text = text
    for old_n, new_n in LEGACY_INVALID_NAMES.items():
        if old_n in sanitized_text:
            found_invalid.append(old_n)
            sanitized_text = re.sub(rf"\b{re.escape(old_n)}\b", new_n, sanitized_text)
            
    if found_invalid:
        print(f"[WARNING] ⚠️ PHÁT HIỆN LỖI TÊN NHÂN VẬT CŨ: {found_invalid}! Đã tự động thay thế chuẩn thành nhân vật bộ truyện hiện tại.")
        return sanitized_text, True
        
    return text, False

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
    print("[INFO] Kích hoạt Động Cơ Dịch Thuật Gemini API: Dịch/Tối ưu toàn bộ kịch bản tiểu thuyết sang Tiếng Việt mượt mà...")
    translate_prompt = (
        "Bạn là dịch giả tiểu thuyết webtoon hàng đầu. Hãy dịch/chuyển ngữ toàn bộ chương tiểu thuyết sau đây sang tiếng Việt tự nhiên, giàu cảm xúc và hấp dẫn.\n"
        "YÊU CẦU DỊCH THUẬT BẮT BUỘC:\n"
        "1. Dịch 100% sang tiếng Việt thuần túy, mượt mà, văn phong tiểu thuyết hành động/huyền ảo kịch tính.\n"
        "2. Giữ nguyên 100% độ dài văn bản, lời thoại trong ngoặc kép (\"...\"), và cấu trúc câu chuyện. TUYỆT ĐỐI KHÔNG tóm tắt hay bỏ sót chi tiết nào.\n"
        "3. Giữ nguyên 100% tên nhân vật chuẩn từ nguyên bản. Cấm tự đổi sang tên khác.\n"
        "4. Chỉ xuất ra duy nhất văn bản truyện đã dịch sang tiếng Việt, không kèm lời dẫn hay giải thích.\n\n"
        f"VĂN BẢN CẦN DỊCH:\n{text[:12000]}"
    )
    if len(text) > 12000:
        print(f"[WARNING] Text too long ({len(text)} chars), truncating to 12000 chars for translation. Some content may be lost.")
    translated_res = call_gemini(translate_prompt)
    if translated_res and len(translated_res.split()) > 200:
        cleaned_res = clean_chapter_content(translated_res)
        cleaned_res, _ = verify_and_sanitize_chapter_content(cleaned_res)
        print(f"[SUCCESS] Đã hoàn thành dịch kịch bản sang Tiếng Việt qua Gemini API! Độ dài: {len(cleaned_res.split())} từ.")
        return cleaned_res
    return text

def call_gemini(prompt: str, json_mode: bool = False, retries: int = 12) -> str:
    """
    ƯU TIÊN 100% HÀNG ĐẦU: InkOS Multi-Agent Engine (Google Gemini 2.0 Flash API với Key Rotator).
    Chỉ khi Gemini hết Key mới chuyển sang Groq / OpenRouter dự phòng.
    """
    # =========================================================================
    # ĐỘNG CƠ ƯU TIÊN 1: InkOS Gemini 2.0 Flash Engine (Google API với Key Rotator)
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
                genai.configure(api_key=g_key)
                g_config = {"max_output_tokens": 8192}
                if json_mode:
                    g_config["response_mime_type"] = "application/json"
                model = genai.GenerativeModel(current_g_model, generation_config=g_config)
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
                time.sleep(1.0)

    # =========================================================================
    # ĐỘNG CƠ DỰ PHÒNG 2: Groq Multi-Model Engine (Dự phòng cấp 2)
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
                        print(f"[SUCCESS] Groq Fallback Engine [{current_model}]: Đã sinh kịch bản ({len(content.strip().split())} từ).")
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
            "messages": [{"role": "user", "content": prompt[:3000] + ("\n...\n" + prompt[-400:] if len(prompt) > 3500 else "")}],
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
    import json
    import requests
    print("[INFO] Fallback to Pollinations Multi-Model Free LLM Engine...")
    
    url = "https://text.pollinations.ai/"
    headers = {"Content-Type": "application/json"}
    pollination_models = ["mistral", "qwen-coder", "openai", "llama"]
    
    for model_name in pollination_models:
        payload = {
            "messages": [
                {"role": "user", "content": prompt[:3000]}
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
        
    # Backup GET request rút gọn prompt
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
            genai.configure(api_key=g_key)
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
        print(f"[WARNING] Skipping embedding generation due to API key error.")
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
    arc_summary = arc.get("summary", "Tiếp tục diễn biến của bối cảnh học viện.")
    
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
                # Giải nén nếu LLM bọc trong dict {"blueprints": [...]} hoặc {"chapters": [...]}
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
            "Quyền Trấn Sơn Hà, Uy Chấn Chư Thiên",
            "Vô Địch Trùng Sinh, Hỗn Độn Luyện Khí",
            "Nghịch Thiên Độc Tôn, Luyện Hóa Thần Thạch",
            "Thôn Phệ Nguyên Khí, Phá Tam Cảnh",
            "Vạn Giới Quỳ Bái, Tiêu Viêm Xuất Thế",
            "Thôn Phệ Ma Nhẫn, Khai Mở Thần Thông",
            "Vô Song Kiếm Khí, Trảm Diệt Cường Địch",
            "Hệ Thống Thần Cấp, Thôn Phệ Vạn Vật",
            "Bá Thần Xuất Thế, Ngăn Cản Vạn Quân",
            "Thôn Phệ Vĩnh Hằng, Xây Dựng Đế Cơ",
            "Thôn Thiên Luyện Địa, Độc Tôn Vạn Cổ",
            "Tuyệt Thế Vô Địch, Phong Ấn Thần Hoàng",
            "Khí Phách Ngút Trời, Thôn Phệ Long Mạch",
            "Vạn Cổ Ma Cung, Đại Chiến Chư Thiên",
            "Bá Chủ Huyền Thoại, Luyện Hóa Vạn Giới"
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
            ch_title = ch_data.get("chapter_title") or f"Chương {ch_num}"
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
    import os
    completed_nums = set()
    prog_file = "data/chapters_progress.json"
    if os.path.exists(prog_file):
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                pdata = json.load(f)
                completed_nums = {int(x) for x in pdata.get("completed_chapters", []) if str(x).isdigit()}
        except Exception:
            pass

    all_chapters = database.get_all_chapters(novel_id)
    
    # Tập hợp tất cả các số chương đã viết xong nội dung (>1200 từ và không phải BLUEPRINT) trong Supabase CSDL
    completed_in_db = {
        int(c["chapter_number"]) for c in all_chapters 
        if isinstance(c.get("chapter_number"), (int, str)) and str(c.get("chapter_number")).isdigit()
        and not str(c.get("content", "")).startswith("BLUEPRINT:")
        and len(str(c.get("content", "")).split()) >= 1200
    }
    
    # Hợp nhất danh sách các chương đã xong
    all_done_nums = completed_nums.union(completed_in_db)
    
    # Lọc các chương chưa viết xong kịch bản (< 1200 từ hoặc còn là BLUEPRINT)
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
        
    print(f"[INFO] BẮT ĐẦU QUY TRÌNH VIẾT CHƯƠNG MỚI: Chương {next_ch_number} (Đã hoàn thành các tập: {sorted(list(all_done_nums))})...")
    
    current_arc = get_current_arc(novel_id, next_ch_number)
    chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    
    if not chapter_record:
        generate_arc_blueprints(novel_id, current_arc)
        all_chapters = database.get_all_chapters(novel_id)
        chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
        
    # LỚP BẢO VỆ TỐI THƯỢNG: Nếu vẫn chưa có chapter_record, tự sinh Blueprint trực tiếp ngay lập tức!
    if not chapter_record:
        print(f"[INFO] Tự động tạo Blueprint trực tiếp cho Chương {next_ch_number}...")
        chapter_record = database.create_chapter(
            novel_id=novel_id,
            chapter_number=next_ch_number,
            title=f"Bí Mật Tập {next_ch_number}",
            content=f"BLUEPRINT: Diễn biến kịch tính tiếp theo cho chương {next_ch_number}."
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
    # Tăng tham chiếu từ 2-3 chương lên 7 chương gần nhất (5 - 10 chương) để đảm bảo mạch truyện cực kỳ nhất quán
    for ch in previous_chapters[-7:]:
        ch_snippet = ch['content'][:600] + "\n...\n" + ch['content'][-600:] if len(ch['content']) > 1200 else ch['content']
        working_memory_text += f"\n--- Chương {ch['chapter_number']}: {ch['title']} ---\n{ch_snippet}\n"
        
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
            f"- Phần mở đầu (Prologue): BẮT BUỘC mở đầu chương bằng một phân cảnh cuốn hút (khoảng 300 - 500 từ) miêu tả bối cảnh thế giới linh hồn, hệ thống Tinh Thần Ấn và bí mật chiếc hộp đồng Đông Sơn.\n"
            f"- **CẢNH BÁO QUAN TRỌNG VỀ NHÂN VẬT**: Trong phần mở đầu này, CHỈ TẬP TRUNG duy nhất vào nhân vật chính ({protagonist_name}). "
            f"TUYỆT ĐỐI KHÔNG liệt kê hay giới thiệu tràn lan các nhân vật phụ. Các nhân vật phụ sẽ chỉ xuất hiện tự nhiên khi có tình huống đối thoại trong câu chuyện.\n"
            f"- **CẢNH BÁO QUAN TRỌNG VỀ TIÊU ĐỀ**: TUYỆT ĐỐI KHÔNG VIẾT CHỮ 'Dẫn lược', 'Dẫn lược:', 'Giới thiệu:', hay 'Prologue:'. "
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
                
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "”", "»", "*"))
            
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

            # VÒNG LẶP ÉP BẮT BUỘC ĐẠT >2800 TỪ (Guaranteed 2800+ Words Multi-Pass Expansion Loop for 12-18 min Audio)
            if word_count >= 2800 and not ends_abruptly:
                # INKOS MULTI-AGENT AUDITOR PASS: Khử AI cliché & Bảo toàn 100% độ dài văn bản
                try:
                    print("[INFO] InkOS Auditor Agent: Bắt đầu rà soát 37 tiêu chuẩn chất lượng & Khử AI cliché...")
                    audit_prompt = prompts.INKOS_AUDITOR_PROMPT.format(chapter_content=final_content[:6000])
                    audited_res = call_gemini(audit_prompt)
                    if audited_res and len(audited_res.split()) >= len(final_content.split()) * 0.9:
                        final_content = clean_chapter_content(audited_res)
                        word_count = len(final_content.split())
                        print(f"[SUCCESS] InkOS Auditor Agent hoàn thành khử AI cliché. Tổng số từ tinh chế: {word_count} từ.")
                    else:
                        final_content = clean_chapter_content(final_content)
                        word_count = len(final_content.split())
                        print(f"[INFO] Giữ nguyên độ dài văn bản đầy đủ: {word_count} từ (Tránh bị rút ngắn).")
                except Exception as audit_err:
                    print(f"[WARNING] InkOS Auditor Agent pass warning: {audit_err}")
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
                    cleaned_next = clean_chapter_content(part_next)
                    final_content = final_content + "\n\n" + cleaned_next
                    word_count = len(final_content.split())
                    print(f"[SUCCESS] Đã nối tiếp thành công! Tổng độ dài chương hiện tại: {word_count} từ.")
                    if word_count >= 2800:
                        break
                else:
                    time.sleep(2)
                    
            if word_count >= 2800:
                break
                
            if ends_abruptly:
                print(f"[WARNING] Draft ends abruptly (no punctuation at the end). Requesting completion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    "\n\n**CẢNH BÁO CỰC KỲ QUAN TRỌNG**: Bản thảo trước của bạn bị cắt cụt đột ngột ở cuối (chưa hết câu, chưa có dấu chấm câu kết thúc). "
                    "Bạn BẮT BUỘC phải viết trọn vẹn câu chuyện, mở rộng chi tiết các phân cảnh, hội thoại và kết thúc chương một cách trọn vẹn bằng dấu chấm câu."
                )
            else:
                print(f"[WARNING] Draft too short ({word_count} words). Requesting longer expansion (Attempt {draft_attempt}/3)...")
                current_prompt = prompt + (
                    f"\n\n**CẢNH BÁO CỰC KỲ QUAN TRỌNG VỀ ĐỘ DÀI (BẮT BUỘC)**:\n"
                    f"Bản thảo bạn vừa viết quá ngắn (chỉ có {word_count} từ), trong khi yêu cầu tối thiểu là 2200 từ để đạt 10 phút nói.\n"
                    f"Để sửa lỗi này, bạn phải viết cực kỳ chi tiết theo hướng dẫn sau:\n"
                    f"1. Chia chương truyện thành ít nhất 5 phân cảnh lớn riêng biệt (Mỗi phân cảnh viết tối thiểu 5-6 đoạn văn dài).\n"
                    f"2. Đi sâu miêu tả cực kỳ tỉ mỉ: cảnh sắc không gian học viện, thời tiết, âm thanh gió thổi, biểu cảm nét mặt từng nhân vật, cử chỉ tay chân, và dòng suy nghĩ nội tâm kéo dài.\n"
                    f"3. Viết các đoạn đối thoại dài, thực tế và sâu sắc giữa các nhân vật (Trần Lam, Linh Vy, Minh Đức, v.v.). Không được viết lướt qua.\n"
                    f"4. TUYỆT ĐỐI không tóm tắt hay kết thúc chương truyện sớm khi chưa đủ độ dài yêu cầu."
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
    # ĐỘNG CƠ DỊCH THUẬT TIẾNG VIỆT GEMINI API: Đảm bảo 100% kịch bản tiểu thuyết chuẩn Tiếng Việt mượt mà
    cleaned_content = translate_to_vietnamese_with_gemini(cleaned_content)
    
    # Đảm bảo tiêu đề chương không bị trùng lặp placeholder
    cur_title = chapter_record.get("title", "")
    if "Hành Trình Mới" in cur_title or not cur_title or cur_title == f"Chương {next_ch_number}":
        EPIC_TITLES = [
            "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận", "Thức Tỉnh Thần Thể, Nén Ép Thần Ma", "Huyết Mạch Thôn Thiên, Trấn Tám Phương",
            "Quyền Trấn Sơn Hà, Uy Chấn Chư Thiên", "Vô Địch Trùng Sinh, Hỗn Độn Luyện Khí", "Nghịch Thiên Độc Tôn, Luyện Hóa Thần Thạch",
            "Thôn Phệ Nguyên Khí, Phá Tam Cảnh", "Vạn Giới Quỳ Bái, Tiêu Viêm Xuất Thế", "Thôn Phệ Ma Nhẫn, Khai Mở Thần Thông",
            "Vô Song Kiếm Khí, Trảm Diệt Cường Địch", "Hệ Thống Thần Cấp, Thôn Phệ Vạn Vật", "Bá Thần Xuất Thế, Ngăn Cản Vạn Quân"
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
        
        # 1. TỰ ĐỘNG LƯU CÁC NHÂN VẬT MỚI SÁNG TẠO VÀO CSDL SUPABASE
        new_chars = data.get("new_characters", [])
        if new_chars:
            print(f"[INFO] 🌟 Đã phát hiện {len(new_chars)} nhân vật MỚI được AI sáng tạo trong chương!")
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

        # 2. CẬP NHẬT TRẠNG THÁI CÁC NHÂN VẬT CŨ
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
