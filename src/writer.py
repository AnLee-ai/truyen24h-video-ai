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

def safe_loads(text: str):
    """Safely parse JSON string, stripping markdown code block wrappers if present."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)

def remove_repetitive_sentences(text: str) -> str:
    """Clean duplicate consecutive sentences or paragraphs."""
    paragraphs = text.split("\n")
    cleaned_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            cleaned_paragraphs.append("")
            continue
        sentences = re.split(r'(?<=[.?!])\s+', para)
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

def call_gemini(prompt: str, json_mode: bool = False, retries: int = 10) -> str:
    """Helper to call LLM (Groq multi-model pool with fallback, otherwise Gemini API) with automatic key rotator & fast 401 failover."""
    groq_key = key_rotator.get_groq_key() or config.GROQ_API_KEY
    
    if groq_key:
        import requests
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        
        groq_models = [
            config.GROQ_MODEL_WRITER,      # "llama-3.3-70b-versatile"
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        max_tokens_options = [3200, 2400, 1800] if not json_mode else [1000]
        
        for attempt in range(retries):
            current_model = groq_models[attempt % len(groq_models)]
            current_max_tokens = max_tokens_options[min(attempt // len(groq_models), len(max_tokens_options)-1)]
            
            data = {
                "model": current_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": current_max_tokens
            }
            if json_mode:
                data["response_format"] = {"type": "json_object"}
                
            try:
                response = requests.post(url, json=data, headers=headers, timeout=120)  # type: ignore[arg-type]
                if response.status_code == 200:
                    resp_json = response.json()
                    content = resp_json["choices"][0]["message"]["content"]
                    if content:
                        return content.strip()
                        
                if response.status_code in (401, 403):
                    print(f"[WARNING] Groq API Key invalid ({response.status_code}). Switching directly to Gemini API...")
                    key_rotator.mark_groq_key_failed(groq_key)
                    break
                    
                if response.status_code == 429:
                    key_rotator.mark_groq_key_failed(groq_key)
                    groq_key = key_rotator.get_groq_key()
                    if not groq_key:
                        break
                    headers["Authorization"] = f"Bearer {groq_key}"
                
                print(f"[WARNING] Groq ({current_model}) status {response.status_code}: {response.text[:120]}. Retrying (Attempt {attempt+1}/{retries})...")
                time.sleep(5)
                continue
            except Exception as e:
                print(f"[WARNING] Groq ({current_model}) error: {e}. Retrying (Attempt {attempt+1}/{retries})...")
                time.sleep(5)
                continue
        
        print("[WARNING] All Groq retries failed. Switching to Gemini API...")

    # Fallback to Gemini API với Key Rotator
    model_name = config.GEMINI_MODEL_WRITER
    
    for attempt in range(retries):
        g_key = key_rotator.get_gemini_key() or config.GEMINI_API_KEY
        if not g_key:
            print("[ERROR] No Gemini API key available.")
            break
            
        try:
            if USE_NEW_GENAI:
                client = get_genai_client(api_key=g_key)
                generation_config = types.GenerateContentConfig(
                    max_output_tokens=8192,
                    response_mime_type="application/json" if json_mode else None
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=generation_config
                )
            else:
                genai.configure(api_key=g_key)
                g_config = {"max_output_tokens": 8192}
                if json_mode:
                    g_config["response_mime_type"] = "application/json"
                model = genai.GenerativeModel(model_name, generation_config=g_config)
                response = model.generate_content(prompt)

            if response.text:
                return response.text.strip()
            raise ValueError("Empty response from Gemini API.")
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "UNAUTHENTICATED" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"[WARNING] Gemini Key bị lỗi {err_str[:80]}. Đang tự động chuyển sang Key tiếp theo...")
                key_rotator.mark_gemini_key_failed(g_key)
                time.sleep(2)
                continue
                
            print(f"[WARNING] Gemini call failed: {e}. Retrying in 5s...")
            time.sleep(5)
            
    print("[WARNING] All API Keys failed (401/429). Switching to Pollinations 100% Free LLM Fallback Engine...")
    free_res = call_pollinations_free_llm(prompt)
    if free_res:
        return free_res
    return "Tiếp tục diễn biến câu chuyện."

def call_pollinations_free_llm(prompt: str) -> str:
    """100% Free Emergency LLM Fallback via Pollinations.ai (Zero API Key needed)."""
    import urllib.parse, urllib.request
    print("[INFO] Fallback to Pollinations 100% Free LLM Engine (Zero API Key needed)...")
    try:
        encoded = urllib.parse.quote(prompt[:2000])
        url = f"https://text.pollinations.ai/{encoded}?model=openai"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            res_text = response.read().decode('utf-8')
            if res_text and len(res_text) > 20 and "402" not in res_text:
                return res_text.strip()
    except Exception as e:
        print(f"[WARNING] Pollinations Free LLM failed: {e}")
    return ""

def get_embedding(text: str) -> list:
    """Generate vector embedding for semantic search using text-embedding-004."""
    g_key = key_rotator.get_gemini_key() or config.GEMINI_API_KEY
    if not g_key:
        return [0.0] * 1536
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

        if len(emb) > 1536:
            return emb[:1536]
        elif len(emb) < 1536:
            return emb + [0.0] * (1536 - len(emb))
        return emb
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "UNAUTHENTICATED" in err_str:
            key_rotator.mark_gemini_key_failed(g_key)
        print(f"[WARNING] Skipping embedding generation due to API key error.")
        return [0.0] * 1536

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
            blueprints = safe_loads(blueprints_json)
            if not isinstance(blueprints, list):
                raise ValueError("Parsed blueprints is not a list")
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

        if not blueprints:
            print("[WARNING] Could not recover any blueprints. Creating default placeholder.")
            blueprints = [{
                "chapter_number": start_ch or 1,
                "chapter_title": "Khởi Đầu Mới",
                "blueprint": "Bắt đầu câu chuyện, giới thiệu nhân vật và thế giới học viện.",
                "characters_present": [],
                "narrative_goal": "Giới thiệu bối cảnh"
            }]

        inserted_chapters = []
        for ch_data in blueprints:
            if not isinstance(ch_data, dict):
                continue
            ch_num = int(ch_data.get("chapter_number", 1))
            ch_title = ch_data.get("chapter_title") or "Chương Tiếp Theo"
            blueprint_text = ch_data.get("blueprint") or "Tiếp tục diễn biến câu chuyện."
            
            ch_record = database.create_chapter(
                novel_id=novel_id,
                chapter_number=ch_num,
                title=ch_title,
                content=f"BLUEPRINT: {blueprint_text}"
            )
            inserted_chapters.append(ch_record)
            
        print(f"[INFO] Created {len(inserted_chapters)} chapter blueprints in DB.")
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
    all_chapters = database.get_all_chapters(novel_id)
    next_ch_record = next((c for c in all_chapters if c["content"].startswith("BLUEPRINT:")), None)
    
    if next_ch_record:
        next_ch_number = next_ch_record["chapter_number"]
    else:
        if all_chapters:
            next_ch_number = all_chapters[-1]["chapter_number"] + 1
        else:
            next_ch_number = 1
        
    print(f"[INFO] Initiating writing process for Chapter {next_ch_number}...")
    
    current_arc = get_current_arc(novel_id, next_ch_number)
    chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
    
    if not chapter_record:
        generate_arc_blueprints(novel_id, current_arc)
        all_chapters = database.get_all_chapters(novel_id)
        chapter_record = next((c for c in all_chapters if c["chapter_number"] == next_ch_number), None)
        
    if not chapter_record:
        raise ValueError(f"Could not initialize blueprint for chapter {next_ch_number}")
        
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
            f"TUYỆT ĐỐI KHÔNG liệt kê hay giới thiệu các nhân vật phụ (như Linh Vy, Minh Đức, Thùy Linh, Cao Bá). Các nhân vật phụ sẽ chỉ xuất hiện tự nhiên khi có tình huống đối thoại trong câu chuyện.\n"
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
            word_count = len(final_content.split())
            print(f"[INFO] Generated draft length: {word_count} words.")
            ends_abruptly = not final_content.strip().endswith((".", "?", "!", '"', "”", "»", "*"))
            
            if ends_abruptly and word_count >= 1500:
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

            if word_count >= 1500 and not ends_abruptly:
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
    client = database.get_client()
    response = client.table("chapters")\
        .update({"content": cleaned_content})\
        .eq("id", chapter_record["id"])\
        .execute()
    updated_chapter = response.data[0] if response.data else {}
    
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
                last_breakthrough_chapter=last_breakthrough_ch
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
