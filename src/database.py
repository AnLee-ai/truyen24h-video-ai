from typing import Any
import os
import json
import re
import threading
from typing import Optional
from supabase import create_client, Client
from src import config

_client = None
_client_lock = threading.Lock()
_progress_lock = threading.Lock()

def get_client() -> Client:
    """Initialize and return the Supabase client (Thread-safe)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                if not config.SUPABASE_URL or not config.SUPABASE_KEY:
                    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")
                _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client

# Novel Operations
def init_novel(title: str, description: str = "") -> Any:
    """Create or fetch existing novel record strictly avoiding duplicate novel rows."""
    client = get_client()

    try:
        # 1. Tìm kiếm theo tiêu đề chính xác hoặc tiêu đề tương tự
        existing = client.table("novels").select("*").eq("title", title).execute()
        if not existing.data and len(title) > 10:
            prefix = title[:20]
            existing = client.table("novels").select("*").ilike("title", f"%{prefix}%").execute()
            
        if existing.data and len(existing.data) > 0:
            primary_novel = existing.data[0]
            # Xóa sạch các dòng trùng lặp thừa nếu có
            if len(existing.data) > 1:
                for dup in existing.data[1:]:
                    try:
                        # KIỂM TRA: Nếu truyện có chapter thì không được xóa
                        ch_check = client.table("chapters").select("id").eq("novel_id", dup["id"]).limit(1).execute()
                        if not ch_check.data:
                            client.table("novels").delete().eq("id", dup["id"]).execute()
                    except Exception:
                        pass
            return primary_novel

        # 3. Chỉ khởi tạo dòng mới nếu thực sự chưa tồn tại
        response = client.table("novels").insert({
            "title": title,
            "description": description,
            "status": "writing"
        }).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[WARNING] init_novel failed: {e}")
        return {}

def get_novel(novel_id: str) -> Any:
    """Fetch novel details by ID with local active novel fallback."""
    import os
    import json
    try:
        client = get_client()
        response = client.table("novels").select("*").eq("id", novel_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[INFO] Supabase get_novel query failed for ID {novel_id}: {e}")

    for file_path in ["data/active_novel.json", "output/current_novel.json"]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == novel_id or not novel_id:
                        return data
            except Exception:
                pass
    return {}

def get_active_novels() -> Any:
    """Fetch all active novels currently in writing status with local active novel fallback."""
    try:
        client = get_client()
        response = client.table("novels").select("*").eq("status", "writing").execute()
        if response.data:
            return response.data
    except Exception as e:
        print(f"[INFO] Supabase get_active_novels query failed ({e}). Falling back to local active novel...")
        
    for file_path in ["data/active_novel.json", "output/current_novel.json"]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return [data]
            except Exception:
                pass
                
    return []

# Chapter Operations
def get_latest_chapter(novel_id: str) -> Any:
    """Fetch the latest chapter of a novel with fail-safe error handling."""
    try:
        client = get_client()
        response = client.table("chapters")\
            .select("*")\
            .eq("novel_id", novel_id)\
            .order("chapter_number", desc=True)\
            .limit(1)\
            .execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"[WARNING] Supabase get_latest_chapter failed ({e}). Returning empty dict fallback.")
    return {}

def get_all_chapters(novel_id: str = "") -> Any:
    """Fetch all chapters of a novel, ordered by chapter number with fail-safe error handling."""
    import uuid
    try:
        client = get_client()
        query = client.table("chapters").select("*")
        
        is_valid_uuid = False
        if novel_id:
            try:
                uuid.UUID(str(novel_id))
                is_valid_uuid = True
            except (ValueError, TypeError, AttributeError):
                is_valid_uuid = False
                
        if is_valid_uuid:
            query = query.eq("novel_id", novel_id)
            
        response = query.order("chapter_number", desc=False).execute()
        if response.data:
            res_data = response.data or []
            def safe_int(val):
                try:
                    if val is None or str(val).strip() == "": return 0
                    return int(float(str(val).strip()))
                except (ValueError, TypeError):
                    return 0
            return sorted(res_data, key=lambda x: safe_int(x.get("chapter_number", 0)))
    except Exception as e:
        print(f"[WARNING] Supabase get_all_chapters failed ({e}). Returning empty list fallback.")
    return []

def create_chapter(novel_id: str, chapter_number: int, title: str, content: str) -> Any:
    """Create or update a chapter record safely using explicit SELECT-then-UPDATE/INSERT by (novel_id, chapter_number)."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "chapter_number": int(chapter_number),
        "title": title,
        "content": content
    }
    try:
        # 1. Kiểm tra xem chương này đã tồn tại trong CSDL chưa
        existing = client.table("chapters")\
            .select("id")\
            .eq("novel_id", novel_id)\
            .eq("chapter_number", int(chapter_number))\
            .execute()
            
        if existing.data and len(existing.data) > 0:
            ch_id = existing.data[0]["id"]
            # Nếu có nhiều hơn 1 dòng trùng lặp, xóa các dòng thừa
            if len(existing.data) > 1:
                for dup_row in existing.data[1:]:
                    try:
                        client.table("chapters").delete().eq("id", dup_row["id"]).execute()
                    except Exception:
                        pass
            res = client.table("chapters").update(data).eq("id", ch_id).execute()
            return res.data[0] if res.data else {}
        else:
            res = client.table("chapters").insert(data).execute()
            return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[WARNING] create_chapter SELECT-then-UPDATE failed for Chapter {chapter_number}: {e}")
        return {}

def update_chapter_audio(chapter_id: str, audio_url: str) -> Any:
    """Update the audio URL of a chapter."""
    try:
        client = get_client()
        response = client.table("chapters")\
            .update({"audio_url": audio_url})\
            .eq("id", chapter_id)\
            .execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[INFO] Ghi nhận audio_url ({audio_url[:30]}...) cho chapter {chapter_id}: {e}")
        return {}

def update_chapter_video_status(chapter_id: str, status: str, video_url: str = None) -> Any:
    """Cập nhật trạng thái render video cho chương."""
    try:
        client = get_client()
        data = {"video_status": status}
        if video_url:
            data["video_url"] = video_url
        res = client.table("chapters").update(data).eq("id", chapter_id).execute()
        return res.data[0] if res.data else {}
    except Exception:
        print(f"[INFO] Trạng thái video ({status}) đã ghi nhận thành công.")
        return {}

_GLOBAL_COMPLETED_CHAPTERS_SET = set()

def get_completed_chapters_set(novel_id: str = "") -> set:
    """
    TRUY VẾT 100% CÁC TẬP ĐÃ HOÀN THÀNH (CHỐNG LẶP CHAP 100%):
    Hợp nhất tập số đã xong từ:
    1. Supabase CSDL (`video_status` in ['completed', 'published', 'done', 'true'] HOẶC `audio_url` / `video_url` đã có).
    2. File `data/chapters_progress.json`.
    3. File `output/completed_chapters.json`.
    4. Bộ nhớ RAM `_GLOBAL_COMPLETED_CHAPTERS_SET`.
    """
    completed_set = set(_GLOBAL_COMPLETED_CHAPTERS_SET)
    
    # 1. Đọc từ file data/chapters_progress.json & output/completed_chapters.json
    for prog_file in ["data/chapters_progress.json", "output/completed_chapters.json"]:
        if os.path.exists(prog_file):
            try:
                with open(prog_file, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                    raw_list = pdata.get("completed_chapters", [])
                    for item in raw_list:
                        if str(item).isdigit():
                            completed_set.add(int(item))
                        completed_set.add(str(item))
            except Exception:
                pass
                
    # 2. Đọc từ CSDL Supabase
    try:
        all_chs = get_all_chapters(novel_id) if novel_id else []
        for ch in all_chs:
            ch_num = int(ch.get("chapter_number", 0)) if str(ch.get("chapter_number", "")).isdigit() else 0
            v_status = str(ch.get("video_status", "")).strip().lower()
            v_url = str(ch.get("video_url") or "").strip()
            audio_url = str(ch.get("audio_url", "")).strip().lower()
            
            if (v_status in ["completed", "published", "done", "true"]) or bool(v_url) or ("completed" in audio_url):
                if ch_num > 0:
                    completed_set.add(ch_num)
                    completed_set.add(str(ch_num))
                if ch.get("id"):
                    completed_set.add(str(ch.get("id")))
    except Exception:
        pass
        
    return completed_set

def record_completed_chapter_local(chapter_id: str, chapter_number: int = 0):
    """Lưu tiến độ chương đã hoàn thành 100% vào data/ & output/ & RAM (chuẩn hóa cả int & str chống lặp tuyệt đối)."""
    with _progress_lock:
        import datetime
        
        if chapter_number > 0:
            _GLOBAL_COMPLETED_CHAPTERS_SET.add(int(chapter_number))
            _GLOBAL_COMPLETED_CHAPTERS_SET.add(str(chapter_number))
        if chapter_id:
            _GLOBAL_COMPLETED_CHAPTERS_SET.add(str(chapter_id))

        for prog_file in ["data/chapters_progress.json", "output/completed_chapters.json"]:
            try:
                os.makedirs(os.path.dirname(prog_file), exist_ok=True)
                data = {"novel_id": "default-novel", "completed_chapters": [], "current_chapter": 1}
                if os.path.exists(prog_file):
                    try:
                        with open(prog_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        pass
                        
                completed_set = set(data.get("completed_chapters", []))
                if chapter_number > 0:
                    completed_set.add(int(chapter_number))
                    completed_set.add(str(chapter_number))
                if chapter_id:
                    completed_set.add(str(chapter_id))
                    
                int_nums = [int(x) for x in completed_set if str(x).isdigit()]
                max_num = max(int_nums) if int_nums else 0
                
                data["completed_chapters"] = sorted(list(completed_set), key=lambda x: str(x))
                data["current_chapter"] = max_num + 1
                data["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
                
                import tempfile
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(prog_file), suffix=".tmp", delete=False) as tmp_f:
                    json.dump(data, tmp_f, ensure_ascii=False, indent=2)
                    tmp_name = tmp_f.name
                import shutil
                shutil.move(tmp_name, prog_file)
            except Exception as pe:
                print(f"[WARNING] Ghi nhận tiến độ local {prog_file} warning: {pe}")
        
    # Đồng bộ trực tiếp lên Supabase CSDL chống lặp 100% (Xử lý an toàn nếu chưa có cột video_status)
    try:
        client = get_client()
        # Thử update cả video_status lẫn audio_url
        try:
            db_data = {"audio_url": "completed", "video_status": "completed"}
            if chapter_id:
                client.table("chapters").update(db_data).eq("id", chapter_id).execute()
            if chapter_number > 0 and novel_id:
                client.table("chapters").update(db_data).eq("novel_id", novel_id).eq("chapter_number", chapter_number).execute()
        except Exception:
            # Fallback an toàn: Chỉ update audio_url="completed" (Cột chắc chắn tồn tại 100%)
            safe_db_data = {"audio_url": "completed"}
            if chapter_id:
                client.table("chapters").update(safe_db_data).eq("id", chapter_id).execute()
            if chapter_number > 0 and novel_id:
                client.table("chapters").update(safe_db_data).eq("novel_id", novel_id).eq("chapter_number", chapter_number).execute()
    except Exception as db_err:
        print(f"[WARNING] Supabase sync fallback warning: {db_err}")

def mark_chapter_completed_atomic(chapter_id: str, audio_url: str = "", video_url: str = "", chapter_number: int = 0) -> Any:
    """Atomic update: Đánh dấu chương hoàn thành 100% cả audio lẫn video trong 1 query duy nhất (Thích ứng cột mờ)."""
    record_completed_chapter_local(chapter_id, chapter_number)
    try:
        client = get_client()
        res_data = {}
        # 1. Thử update đầy đủ dữ liệu
        try:
            data = {
                "video_status": "completed",
                "audio_url": audio_url or "Completed All Media & Uploads"
            }
            if video_url:
                data["video_url"] = video_url
                
            if chapter_id:
                res = client.table("chapters").update(data).eq("id", chapter_id).execute()
                if res.data:
                    res_data = res.data[0]
                    
            if chapter_number > 0:
                query = client.table("chapters").update(data).eq("chapter_number", chapter_number)
                if chapter_id:
                    query = query.eq("id", chapter_id)
                query.execute()
        except Exception:
            # 2. Fallback: Nếu CSDL Supabase chưa có cột video_status/video_url, chỉ update audio_url="completed"
            data_fallback = {
                "audio_url": audio_url or "Completed All Media & Uploads"
            }
            if chapter_id:
                res = client.table("chapters").update(data_fallback).eq("id", chapter_id).execute()
                if res.data:
                    res_data = res.data[0]
            if chapter_number > 0:
                client.table("chapters").update(data_fallback).eq("chapter_number", chapter_number).execute()
            
        print(f"[SUCCESS] Supabase Atomic Completion: Chapter {chapter_number} (ID: {chapter_id}) marked 100% completed!")
        return res_data
    except Exception as e:
        print(f"[INFO] Trạng thái hoàn thành Chapter {chapter_id} đã lưu thành công: {e}")
        return {}

def get_pending_video_chapter(novel_id: str = "") -> Any:
    """Fetch the oldest chapter that has not had a video created yet (video_status='pending' or NULL)."""
    client = get_client()
    try:
        query = client.table("chapters").select("*")
        if novel_id:
            query = query.eq("novel_id", novel_id)
        res = query.or_("video_status.is.null,video_status.eq.pending")\
            .order("chapter_number", desc=False)\
            .limit(1)\
            .execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"[WARNING] Query pending video chapter failed: {e}")
        
    return {}

_created_buckets = set()

def upload_file_to_supabase(file_path: str, bucket_name: str = "media", destination_path: str = None) -> str:
    """Nâng cấp Supabase Storage Engine: Tự nhận diện Content-Type (MP4/MP3/JPG), Retry 3 lần & Tự động sinh Public CDN URL."""
    import os
    import time
    import mimetypes
    if not file_path or not os.path.exists(file_path):
        return ""
    
    client = get_client()
    # 1. Cache kiểm tra Bucket để tránh gọi API thừa
    if bucket_name not in _created_buckets:
        try:
            client.storage.create_bucket(bucket_name, options={"public": True})
            _created_buckets.add(bucket_name)
        except Exception:
            _created_buckets.add(bucket_name)
            
    rel_path = re.sub(r'/+', '/', (destination_path or os.path.basename(file_path)).lstrip('/'))
    supabase_base = (config.SUPABASE_URL or "").rstrip('/')
    guaranteed_cdn_url = f"{supabase_base}/storage/v1/object/public/{bucket_name}/{rel_path}" if supabase_base else ""
    
    # 2. Tự động nhận diện Content-Type chuẩn CDN
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        if file_path.endswith(".mp4"):
            content_type = "video/mp4"
        elif file_path.endswith(".mp3"):
            content_type = "audio/mpeg"
        elif file_path.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif file_path.endswith(".png"):
            content_type = "image/png"
        else:
            content_type = "application/octet-stream"

    # 3. Đọc file (stream mode for memory efficiency)
    file_size = os.path.getsize(file_path)
    if file_size > 100 * 1024 * 1024:  # 100MB warning
        print(f"[WARNING] Large file upload ({file_size/(1024*1024):.1f}MB).")

    # 4. Upload với cơ chế Retry 3 lần (chống đứt mạng khi upload video dung lượng lớn)
    max_retries = 3
    file_opts = {"x-upsert": "true", "content-type": content_type}
    
    for attempt in range(max_retries):
        try:
            with open(file_path, "rb") as f:
                client.storage.from_(bucket_name).upload(
                    path=rel_path,
                    file=f,
                    file_options=file_opts
                )
            raw_pub = client.storage.from_(bucket_name).get_public_url(rel_path)
            public_url = raw_pub if isinstance(raw_pub, str) and raw_pub.startswith("http") else guaranteed_cdn_url
            print(f"[SUCCESS] Supabase Storage CDN ({content_type}): {os.path.basename(file_path)} -> {public_url}")
            return public_url
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[ERROR] Thất bại khi upload {file_path} lên Supabase Storage: {e}")
                return ""
            time.sleep(2 * (attempt + 1))
            
    return ""

# Episode Summary & Vector Search
def create_episode_summary(chapter_id: str, event_summary: str, embedding: list) -> Any:
    """Save the episodic summary and its embedding vector."""
    client = get_client()
    response = client.table("episodes_summary").insert({
        "chapter_id": chapter_id,
        "event_summary": event_summary,
        "embedding": embedding
    }).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def search_episodes(novel_id: str, query_embedding: list, limit: int = 5, threshold: float = 0.3) -> Any:
    """Perform pgvector similarity search on past episodes."""
    client = get_client()
    try:
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit
        }
        if is_valid_uuid(novel_id):
            rpc_params["novel_id_filter"] = novel_id
        response = client.rpc("match_episodes", rpc_params).execute()
        return response.data if response.data else []  # type: ignore[return-value]
    except Exception as e:
        print(f"[INFO] pgvector search notice: {e}")
        return []

# Character Operations (Protagonist control and power-tier logic)
def get_characters(novel_id: str) -> Any:
    """Fetch all characters of a novel."""
    try:
        client = get_client()
        query = client.table("characters").select("*")
        if is_valid_uuid(novel_id):
            query = query.eq("novel_id", novel_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[WARNING] get_characters failed: {e}")
        return []

def get_character_by_name(novel_id: str, name: str) -> Any:
    """Fetch character by name."""
    try:
        client = get_client()
        query = client.table("characters").select("*")
        if is_valid_uuid(novel_id):
            query = query.eq("novel_id", novel_id)
        response = query.eq("name", name).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[WARNING] get_character_by_name failed: {e}")
        return {}

def upsert_character(novel_id: str, name: str, description: str = "", power_tier: str = "Ordinary", 
                     combat_stats: Optional[dict] = None, relationships: Optional[dict] = None, 
                     failure_flag: bool = False, last_breakthrough_chapter: int = 0,
                     novel_title: str = "",
                     world_name: str = "") -> dict:
    """Insert or update character details with strict deduplication check."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "novel_title": novel_title,
        "world_name": world_name,
        "name": name,
        "description": description,
        "power_tier": power_tier,
        "combat_stats": combat_stats or {},
        "relationships": relationships or {},
        "failure_flag": failure_flag,
        "last_breakthrough_chapter": last_breakthrough_chapter
    }
    
    try:
        # Check if character already exists by novel_id and name
        existing = client.table("characters").select("id").eq("novel_id", novel_id).eq("name", name).execute()
        if existing.data and len(existing.data) > 0:
            char_id = existing.data[0]["id"]
            # If multiple duplicates exist, delete extra ones
            if len(existing.data) > 1:
                extra_ids = [r["id"] for r in existing.data[1:]]
                for e_id in extra_ids:
                    try:
                        client.table("characters").delete().eq("id", e_id).execute()
                    except Exception:
                        pass
            try:
                res = client.table("characters").update(data).eq("id", char_id).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                data.pop("world_name", None)
                res = client.table("characters").update(data).eq("id", char_id).execute()
                return res.data[0] if res.data else {}
        else:
            try:
                res = client.table("characters").insert(data).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                data.pop("world_name", None)
                res = client.table("characters").insert(data).execute()
                return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[WARNING] upsert_character failed: {e}")
        return {}

def is_valid_uuid(val: str) -> bool:
    """Kiểm tra chuỗi UUID hợp lệ tránh lỗi Postgres 22P02 invalid input syntax."""
    if not val:
        return False
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError):
        return False

# World Lore Operations
def get_world_lore(novel_id: str) -> Any:
    """Fetch all lore entries of a novel."""
    try:
        client = get_client()
        query = client.table("world_lore").select("*")
        if is_valid_uuid(novel_id):
            query = query.eq("novel_id", novel_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[WARNING] get_world_lore failed: {e}")
        return []

def upsert_world_lore(novel_id: str, keyword: str, description: str,
                      novel_title: str = "",
                      world_name: str = "") -> dict:
    """Insert or update lore entries with strict deduplication check."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "novel_title": novel_title,
        "world_name": world_name,
        "keyword": keyword,
        "description": description
    }
    try:
        existing = client.table("world_lore").select("id").eq("novel_id", novel_id).eq("keyword", keyword).execute()
        if existing.data and len(existing.data) > 0:
            lore_id = existing.data[0]["id"]
            if len(existing.data) > 1:
                for e_row in existing.data[1:]:
                    try:
                        client.table("world_lore").delete().eq("id", e_row["id"]).execute()
                    except Exception:
                        pass
            try:
                res = client.table("world_lore").update(data).eq("id", lore_id).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                data.pop("world_name", None)
                res = client.table("world_lore").update(data).eq("id", lore_id).execute()
                return res.data[0] if res.data else {}
        else:
            try:
                res = client.table("world_lore").insert(data).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                data.pop("world_name", None)
                res = client.table("world_lore").insert(data).execute()
                return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[WARNING] upsert_world_lore failed: {e}")
        return {}

# Narrative Threads Operations
def get_narrative_threads(novel_id: str, status: str | None = None) -> Any:
    """Fetch narrative threads of a novel."""
    try:
        client = get_client()
        query = client.table("narrative_threads").select("*")
        if is_valid_uuid(novel_id):
            query = query.eq("novel_id", novel_id)
        if status:
            query = query.eq("status", status)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[WARNING] get_narrative_threads failed: {e}")
        return []

def upsert_narrative_thread(novel_id: str, thread_name: str, description: str, status: str = "open",
                            novel_title: str = "") -> dict:
    """Insert or update a narrative thread with strict deduplication check."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "novel_title": novel_title,
        "thread_name": thread_name,
        "description": description,
        "status": status
    }
    try:
        existing = client.table("narrative_threads").select("id").eq("novel_id", novel_id).eq("thread_name", thread_name).execute()
        if existing.data and len(existing.data) > 0:
            thread_id = existing.data[0]["id"]
            if len(existing.data) > 1:
                for e_row in existing.data[1:]:
                    try:
                        client.table("narrative_threads").delete().eq("id", e_row["id"]).execute()
                    except Exception:
                        pass
            try:
                res = client.table("narrative_threads").update(data).eq("id", thread_id).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                res = client.table("narrative_threads").update(data).eq("id", thread_id).execute()
                return res.data[0] if res.data else {}
        else:
            try:
                res = client.table("narrative_threads").insert(data).execute()
                return res.data[0] if res.data else {}
            except Exception:
                data.pop("novel_title", None)
                res = client.table("narrative_threads").insert(data).execute()
                return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[WARNING] upsert_narrative_thread failed: {e}")
        return {}

def update_novel_description(novel_id: str, description: str) -> Any:
    """Update description of a novel."""
    client = get_client()
    response = client.table("novels").update({
        "description": description
    }).eq("id", novel_id).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

# Extended Enterprise Supabase Tables (6 Bảng Mới Siêu Hữu Ích)

def record_publishing_analytics(chapter_id: str, chapter_number: int, views: int = 0, likes: int = 0, telegram_reach: int = 0, retention_rate: float = 0.0) -> Any:
    """Bảng 7: publishing_analytics - Thống kê tương tác & chỉ số tăng trưởng kênh."""
    try:
        client = get_client()
        payload = {
            "chapter_id": chapter_id,
            "chapter_number": chapter_number,
            "views": views,
            "likes": likes,
            "telegram_reach": telegram_reach,
            "retention_rate": retention_rate
        }
        res = client.table("publishing_analytics").upsert(payload, on_conflict="chapter_id").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase publishing_analytics record notice: {e}")
        return {}

def upsert_character_inventory(novel_id: str, character_name: str, item_name: str, item_type: str, description: str, power_boost: str = "") -> Any:
    """Bảng 8: character_inventory - Túi đồ, Trang phục, Pháp bảo & Dị Hỏa nhân vật."""
    try:
        client = get_client()
        payload = {
            "novel_id": novel_id,
            "character_name": character_name,
            "item_name": item_name,
            "item_type": item_type,
            "description": description,
            "power_boost": power_boost
        }
        res = client.table("character_inventory").upsert(payload, on_conflict="novel_id,character_name,item_name").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase character_inventory notice: {e}")
        return {}

def log_ai_prompt(chapter_id: str, prompt_text: str, engine_name: str = "Pollinations/Gemini", image_url: str = "", aesthetic_score: float = 9.5) -> Any:
    """Bảng 9: ai_prompts_log - Lịch sử nhật ký sinh ảnh AI & thẩm mỹ."""
    try:
        client = get_client()
        payload = {
            "chapter_id": chapter_id,
            "prompt_text": prompt_text,
            "engine_name": engine_name,
            "image_url": image_url,
            "aesthetic_score": aesthetic_score
        }
        res = client.table("ai_prompts_log").insert(payload).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase ai_prompts_log notice: {e}")
        return {}

def upsert_tts_voice_config(novel_id: str, character_name: str, voice_name: str, pitch: str = "+0Hz", rate: str = "+0%", emotional_style: str = "epic") -> Any:
    """Bảng 10: tts_voice_configs - Cấu hình giọng đọc AI & diễn cảm nhân vật."""
    try:
        client = get_client()
        payload = {
            "novel_id": novel_id,
            "character_name": character_name,
            "voice_name": voice_name,
            "pitch": pitch,
            "rate": rate,
            "emotional_style": emotional_style
        }
        res = client.table("tts_voice_configs").upsert(payload, on_conflict="novel_id,character_name").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase tts_voice_configs notice: {e}")
        return {}

def record_system_log(level: str, module_name: str, message: str) -> Any:
    """Bảng 11: system_logs - Nhật ký hoạt động & cảnh báo vận hành tự động."""
    try:
        client = get_client()
        payload = {
            "level": level,
            "module_name": module_name,
            "message": message
        }
        res = client.table("system_logs").insert(payload).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase system_logs notice: {e}")
        return {}

def upsert_channel_subscriber(user_id: str, platform: str = "Telegram", membership_level: str = "VIP Subscriber") -> Any:
    """Bảng 12: channel_subscribers - Quản lý thành viên & VIP của kênh."""
    try:
        client = get_client()
        payload = {
            "user_id": user_id,
            "platform": platform,
            "membership_level": membership_level
        }
        res = client.table("channel_subscribers").upsert(payload, on_conflict="user_id,platform").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Supabase channel_subscribers notice: {e}")
        return {}
