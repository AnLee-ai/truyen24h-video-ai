from src import database

client = database.get_client()
res = client.table('chapters').select('id, chapter_number, title, content_status, video_status, video_url').order('chapter_number').execute()

for r in res.data:
    if r['chapter_number'] <= 6:
        print(f"Chương {r['chapter_number']}: content={r['content_status']}, video={r['video_status']}, url={r['video_url']}")
