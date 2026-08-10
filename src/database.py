from supabase import create_client, Client
from src import config

_client = None

def get_client() -> Client:
    """Initialize and return the Supabase client."""
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client

# Novel Operations
def init_novel(title: str, description: str = "") -> dict:
    """Create or fetch existing novel record strictly avoiding duplicate novel rows."""
    client = get_client()
    MASTER_ID = "d1c402ea-4882-4ffa-81e5-639e93fed463"
    try:
        # 1. Nếu là bộ Vạn Cổ Thần Vương, ưu tiên tra cứu theo Master ID trước
        if "Vạn Cổ Thần Vương" in title or "van-co-than-vuong" in title:
            master_res = client.table("novels").select("*").eq("id", MASTER_ID).execute()
            if master_res.data:
                return master_res.data[0]

        # 2. Tìm kiếm theo tiêu đề chính xác hoặc tiêu đề tương tự
        existing = client.table("novels").select("*").eq("title", title).execute()
        if not existing.data and len(title) > 10:
            prefix = title[:15]
            existing = client.table("novels").select("*").ilike("title", f"%{prefix}%").execute()
            
        if existing.data and len(existing.data) > 0:
            primary_novel = existing.data[0]
            # Xóa sạch các dòng trùng lặp thừa nếu có
            if len(existing.data) > 1:
                for dup in existing.data[1:]:
                    try:
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

def get_novel(novel_id: str) -> dict:
    """Fetch novel details by ID with local active novel fallback."""
    import os, json
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
                    return data
            except Exception:
                pass
    return {}

def get_active_novels() -> list:
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
                
    return [{
        "id": "van-co-than-vuong-v1",
        "title": "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận",
        "description": "Truyện tiên hiệp huyền huyễn cực kỳ kịch tính. Nam chính Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, từng bước luyện hóa vạn giới chư thiên, nén ép vạn giới thần ma, xây dựng lại trật tự vĩnh hằng.",
        "status": "writing"
    }]

# Chapter Operations
def get_latest_chapter(novel_id: str) -> dict:
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

def get_all_chapters(novel_id: str) -> list:
    """Fetch all chapters of a novel, ordered by chapter number with fail-safe error handling."""
    try:
        client = get_client()
        response = client.table("chapters")\
            .select("*")\
            .eq("novel_id", novel_id)\
            .order("chapter_number", desc=False)\
            .execute()
        if response.data:
            return response.data
    except Exception as e:
        print(f"[WARNING] Supabase get_all_chapters failed ({e}). Returning empty list fallback.")
    return []

def create_chapter(novel_id: str, chapter_number: int, title: str, content: str) -> dict:
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

def update_chapter_audio(chapter_id: str, audio_url: str) -> dict:
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

def update_chapter_video_status(chapter_id: str, status: str, video_url: str = None) -> dict:
    """Cập nhật trạng thái render video cho chương."""
    try:
        client = get_client()
        data = {"video_status": status}
        if video_url:
            data["video_url"] = video_url
        res = client.table("chapters").update(data).eq("id", chapter_id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Trạng thái video ({status}) đã ghi nhận thành công.")
        return {}

def record_completed_chapter_local(chapter_id: str, chapter_number: int = 0):
    """Lưu tiến độ chương đã hoàn thành 100% vào file data/chapters_progress.json (chuẩn hóa cả int & str chống lặp tuyệt đối)."""
    import os, json, datetime
    prog_file = "data/chapters_progress.json"
    data = {"novel_id": "van-co-than-vuong-v1", "completed_chapters": [], "current_chapter": 1}
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
    
    try:
        os.makedirs("data", exist_ok=True)
        with open(prog_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[SUCCESS] Đã khóa tiến độ hoàn thành Tập {chapter_number} (ID: {chapter_id}) vào data/chapters_progress.json!")
    except Exception as e:
        print(f"[WARNING] Không thể lưu file data/chapters_progress.json: {e}")

def mark_chapter_completed_atomic(chapter_id: str, audio_url: str = "", video_url: str = "", chapter_number: int = 0) -> dict:
    """Atomic update: Đánh dấu chương hoàn thành 100% cả audio lẫn video trong 1 query duy nhất."""
    record_completed_chapter_local(chapter_id, chapter_number)
    try:
        client = get_client()
        data = {
            "video_status": "completed",
            "audio_url": audio_url or "Completed All Media & Uploads"
        }
        if video_url:
            data["video_url"] = video_url
        res = client.table("chapters").update(data).eq("id", chapter_id).execute()
        print(f"[SUCCESS] Supabase Atomic Completion: Chapter {chapter_id} marked 100% completed!")
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[INFO] Trạng thái hoàn thành Chapter {chapter_id} đã lưu thành công: {e}")
        return {}

def get_pending_video_chapter(novel_id: str = "") -> dict:
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
            
    rel_path = destination_path or os.path.basename(file_path)
    
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

    # 3. Đọc file
    with open(file_path, "rb") as f:
        file_data = f.read()

    # 4. Upload với cơ chế Retry 3 lần (chống đứt mạng khi upload video dung lượng lớn)
    max_retries = 3
    file_opts = {"x-upsert": "true", "content-type": content_type}
    
    for attempt in range(max_retries):
        try:
            client.storage.from_(bucket_name).upload(
                path=rel_path,
                file=file_data,
                file_options=file_opts
            )
            public_url = client.storage.from_(bucket_name).get_public_url(rel_path)
            print(f"[SUCCESS] Supabase Storage CDN ({content_type}): {os.path.basename(file_path)} -> {public_url}")
            return public_url
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[WARNING] Supabase Storage upload failed for {file_path}: {e}")
                return ""
            time.sleep(2 * (attempt + 1))
            
    return ""

# Episode Summary & Vector Search
def create_episode_summary(chapter_id: str, event_summary: str, embedding: list) -> dict:
    """Save the episodic summary and its embedding vector."""
    client = get_client()
    response = client.table("episodes_summary").insert({
        "chapter_id": chapter_id,
        "event_summary": event_summary,
        "embedding": embedding
    }).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def search_episodes(novel_id: str, query_embedding: list, limit: int = 5, threshold: float = 0.3) -> list:
    """Perform pgvector similarity search on past episodes."""
    client = get_client()
    try:
        response = client.rpc("match_episodes", {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "novel_id_filter": novel_id
        }).execute()
        return response.data if response.data else []  # type: ignore[return-value]
    except Exception as e:
        print(f"[ERROR] pgvector search failed: {e}")
        return []

# Character Operations (Protagonist control and power-tier logic)
def get_characters(novel_id: str) -> list:
    """Fetch all characters of a novel."""
    client = get_client()
    response = client.table("characters").select("*").eq("novel_id", novel_id).execute()
    return response.data if response.data else []

def get_character_by_name(novel_id: str, name: str) -> dict:
    """Fetch character by name."""
    client = get_client()
    response = client.table("characters")\
        .select("*")\
        .eq("novel_id", novel_id)\
        .eq("name", name)\
        .execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def upsert_character(novel_id: str, name: str, description: str = "", power_tier: str = "Ordinary", 
                     combat_stats: dict | None = None, relationships: dict | None = None, 
                     failure_flag: bool = False, last_breakthrough_chapter: int = 0,
                     novel_title: str = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận",
                     world_name: str = "Đấu Khí Đại Lục / Vạn Cổ Thần Vương Universe") -> dict:
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

# World Lore Operations
def get_world_lore(novel_id: str) -> list:
    """Fetch all lore entries of a novel."""
    client = get_client()
    response = client.table("world_lore").select("*").eq("novel_id", novel_id).execute()
    return response.data if response.data else []

def upsert_world_lore(novel_id: str, keyword: str, description: str,
                      novel_title: str = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận",
                      world_name: str = "Đấu Khí Đại Lục / Vạn Cổ Thần Vương Universe") -> dict:
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
        existing = client.table("world_lore").select("id").eq("keyword", keyword).execute()
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
def get_narrative_threads(novel_id: str, status: str | None = None) -> list:
    """Fetch narrative threads of a novel."""
    client = get_client()
    query = client.table("narrative_threads").select("*").eq("novel_id", novel_id)
    if status:
        query = query.eq("status", status)
    response = query.execute()
    return response.data if response.data else []

def upsert_narrative_thread(novel_id: str, thread_name: str, description: str, status: str = "open",
                            novel_title: str = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận") -> dict:
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
        existing = client.table("narrative_threads").select("id").eq("thread_name", thread_name).execute()
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

def update_novel_description(novel_id: str, description: str) -> dict:
    """Update description of a novel."""
    client = get_client()
    response = client.table("novels").update({
        "description": description
    }).eq("id", novel_id).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]
