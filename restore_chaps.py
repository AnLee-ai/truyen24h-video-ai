from src.database import get_client
import uuid
client = get_client()

novel_id = 'd1c402ea-4882-4ffa-81e5-639e93fed463'
chaps_to_insert = [
    {"chapter_number": 1, "title": "Trùng Sinh Học Viện, Thôn Phệ Phế Đan"},
    {"chapter_number": 2, "title": "Chấn Động Ngoại Viện, Một Quyền Phá Lực"},
    {"chapter_number": 3, "title": "Tàng Kinh Các, Thượng Cổ Tàn Chiêu"}
]

for c in chaps_to_insert:
    print(f"Recreating chapter {c['chapter_number']}")
    client.table("chapters").insert({
        "id": str(uuid.uuid4()),
        "novel_id": novel_id,
        "chapter_number": c["chapter_number"],
        "title": c["title"],
        "content": "BLUEPRINT: Reset for regeneration",
        "video_status": "pending"
    }).execute()

print("Restored 3 chapters successfully.")
