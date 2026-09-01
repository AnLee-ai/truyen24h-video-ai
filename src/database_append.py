def get_novel_id_from_chapter(chapter_id: str) -> str:
    """Fetch novel_id from a chapter_id."""
    try:
        client = get_client()
        response = client.table("chapters").select("novel_id").eq("id", chapter_id).execute()
        if response.data:
            return response.data[0].get("novel_id", "")
    except Exception as e:
        print(f"[WARNING] get_novel_id_from_chapter failed: {e}")
    return ""
