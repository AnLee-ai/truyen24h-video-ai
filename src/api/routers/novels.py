from fastapi import APIRouter
from src import database

router = APIRouter()

@router.get("/novels")
def api_get_novels():
    """Lấy danh sách các truyện đang active từ DB."""
    try:
        novels = database.get_active_novels()
        if not novels:
            return {"status": "success", "data": []}
            
        data = []
        for n in novels:
            latest = database.get_latest_chapter(n["id"])
            latest_num = latest.get("chapter_number", 0) if latest else 0
            data.append({
                "id": n["id"],
                "title": n["title"],
                "status": n.get("status", "writing"),
                "latest_chapter": latest_num
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
