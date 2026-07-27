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
    """Create a new chapter record."""
    client = get_client()
    response = client.table("chapters").insert({
        "novel_id": novel_id,
        "chapter_number": chapter_number,
        "title": title,
        "content": content
    }).execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def update_chapter_audio(chapter_id: str, audio_url: str) -> dict:
    """Update the audio URL of a chapter."""
    client = get_client()
    response = client.table("chapters")\
        .update({"audio_url": audio_url})\
        .eq("id", chapter_id)\
        .execute()
    return response.data[0] if response.data else {}  # type: ignore[return-value]

def update_chapter_video_status(chapter_id: str, status: str = "completed", video_url: str = "") -> dict:
    """Update video creation status and video URL of a chapter in Supabase."""
    client = get_client()
    update_data = {"video_status": status}
    if video_url:
        update_data["video_url"] = video_url
    try:
        response = client.table("chapters")\
            .update(update_data)\
            .eq("id", chapter_id)\
            .execute()
        return response.data[0] if response.data else {}  # type: ignore[return-value]
    except Exception as e:
        print(f"[WARNING] Could not update video_status in Supabase: {e}")
        return {}

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
