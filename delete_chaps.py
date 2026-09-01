from src.database import get_all_chapters, get_client
client = get_client()

chapters = get_all_chapters('d1c402ea-4882-4ffa-81e5-639e93fed463')
for c in chapters:
    print(f"Chapter {c['chapter_number']}: {c['id']} - Audio: {c.get('audio_status')}, Video: {c.get('video_status')}")

# Delete chapters 1, 2, 3
for c in chapters:
    if c['chapter_number'] in [1, 2, 3]:
        print(f"Deleting chapter {c['chapter_number']} ({c['id']})")
        client.table("chapters").delete().eq("id", c['id']).execute()
print("Done deleting 3 chapters.")
