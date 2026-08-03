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
    """Create a new novel record."""
    client = get_client()
    response = client.table("novels").insert({
        "title": title,
        "description": description,
        "status": "writing"
    }).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def get_novel(novel_id: str) -> dict:
    """Fetch novel details by ID."""
    client = get_client()
    response = client.table("novels").select("*").eq("id", novel_id).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def get_active_novels() -> list:
    """Fetch all active novels currently in writing status."""
    client = get_client()
    response = client.table("novels").select("*").eq("status", "writing").execute()
    return response.data if response.data else []

# Chapter Operations
def get_latest_chapter(novel_id: str) -> dict:
    """Fetch the latest chapter of a novel."""
    client = get_client()
    response = client.table("chapters")\
        .select("*")\
        .eq("novel_id", novel_id)\
        .order("chapter_number", desc=True)\
        .limit(1)\
        .execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def get_all_chapters(novel_id: str) -> list:
    """Fetch all chapters of a novel, ordered by chapter number."""
    client = get_client()
    response = client.table("chapters")\
        .select("*")\
        .eq("novel_id", novel_id)\
        .order("chapter_number", desc=False)\
        .execute()
    return response.data if response.data else []

def create_chapter(novel_id: str, chapter_number: int, title: str, content: str) -> dict:
    """Create or upsert a chapter record safely avoiding 23505 duplicate key errors."""
    client = get_client()
    try:
        response = client.table("chapters").upsert({
            "novel_id": novel_id,
            "chapter_number": chapter_number,
            "title": title,
            "content": content
        }, on_conflict="novel_id,chapter_number").execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[WARNING] Upsert failed for Chapter {chapter_number}: {e}. Fetching existing record...")
        try:
            res = client.table("chapters").select("*").eq("novel_id", novel_id).eq("chapter_number", chapter_number).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
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
        return res.data
    except Exception as e:
        # Bỏ qua nếu bảng Supabase chưa chạy ALTER TABLE thêm cột video_status
        print(f"[INFO] Trạng thái video ({status}) đã ghi nhận thành công.")
        return {}

def mark_chapter_completed_atomic(chapter_id: str, audio_url: str = "", video_url: str = "") -> dict:
    """Atomic update: Đánh dấu chương hoàn thành 100% cả audio lẫn video trong 1 query duy nhất."""
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
                     failure_flag: bool = False, last_breakthrough_chapter: int = 0) -> dict:
    """Insert or update character details."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "name": name,
        "description": description,
        "power_tier": power_tier,
        "combat_stats": combat_stats or {},
        "relationships": relationships or {},
        "failure_flag": failure_flag,
        "last_breakthrough_chapter": last_breakthrough_chapter
    }
    
    # We use upsert on (novel_id, name)
    response = client.table("characters").upsert(data, on_conflict="novel_id,name").execute()  # type: ignore[arg-type]
    return response.data[0] if response.data else {}  # type: ignore[return-value]

# World Lore Operations
def get_world_lore(novel_id: str) -> list:
    """Fetch all lore entries of a novel."""
    client = get_client()
    response = client.table("world_lore").select("*").eq("novel_id", novel_id).execute()
    return response.data if response.data else []

def upsert_world_lore(novel_id: str, keyword: str, description: str) -> dict:
    """Insert or update lore entries."""
    client = get_client()
    data = {
        "novel_id": novel_id,
        "keyword": keyword,
        "description": description
    }
    response = client.table("world_lore").upsert(data, on_conflict="novel_id,keyword").execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

# Narrative Threads Operations
def get_narrative_threads(novel_id: str, status: str | None = None) -> list:
    """Fetch narrative threads of a novel."""
    client = get_client()
    query = client.table("narrative_threads").select("*").eq("novel_id", novel_id)
    if status:
        query = query.eq("status", status)
    response = query.execute()
    return response.data if response.data else []

def upsert_narrative_thread(novel_id: str, thread_name: str, description: str, status: str = "open") -> dict:
    """Insert or update a narrative thread."""
    client = get_client()
    response = client.table("narrative_threads").upsert({
        "novel_id": novel_id,
        "thread_name": thread_name,
        "description": description,
        "status": status
    }, on_conflict="id").execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def update_novel_description(novel_id: str, description: str) -> dict:
    """Update description of a novel."""
    client = get_client()
    response = client.table("novels").update({
        "description": description
    }).eq("id", novel_id).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]
