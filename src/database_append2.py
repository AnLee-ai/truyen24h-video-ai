
def get_novel_genre_info(novel_id: str) -> str:
    """Fetch genre and description for context enrichment."""
    try:
        if not novel_id: return "Epic Fantasy / Action"
        client = get_client()
        response = client.table("novels").select("genre, description").eq("id", novel_id).execute()
        if response.data:
            genre = response.data[0].get("genre", "")
            desc = response.data[0].get("description", "")
            return f"Genre: {genre} | Lore: {desc[:200]}"
    except Exception:
        pass
    return "Epic Fantasy / Action"
