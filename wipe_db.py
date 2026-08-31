import os
from src.database import get_client

client = get_client()

print("Deleting all chapters...")
res_chapters = client.table("chapters").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
print(f"Deleted chapters: {len(res_chapters.data) if hasattr(res_chapters, 'data') else 'Unknown'}")

print("Deleting all episode summaries...")
res_episodes = client.table("episodes_summary").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
print(f"Deleted episodes summaries: {len(res_episodes.data) if hasattr(res_episodes, 'data') else 'Unknown'}")

print("Done resetting database!")
