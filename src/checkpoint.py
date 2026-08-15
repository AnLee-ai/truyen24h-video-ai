import os
import json

def get_checkpoint_path(chapter_id: str) -> str:
    """Returns the path to the checkpoint.json file for a given chapter."""
    chapter_dir = os.path.join("output", chapter_id)
    os.makedirs(chapter_dir, exist_ok=True)
    return os.path.join(chapter_dir, "checkpoint.json")

def load_checkpoint(chapter_id: str) -> dict:
    """Loads the checkpoint data, or returns a default dictionary if not found."""
    path = get_checkpoint_path(chapter_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "is_written": False,
        "is_audio_done": False,
        "is_image_done": False,
        "is_video_done": False,
        "audio_path": "",
        "srt_path": "",
        "video_path": ""
    }

def save_checkpoint(chapter_id: str, data: dict):
    """Saves the checkpoint data to disk."""
    path = get_checkpoint_path(chapter_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[WARNING] Failed to save checkpoint for {chapter_id}: {e}")

def mark_step_done(chapter_id: str, step: str, **kwargs):
    """Marks a specific step as done and saves optional metadata."""
    data = load_checkpoint(chapter_id)
    data[step] = True
    for k, v in kwargs.items():
        data[k] = v
    save_checkpoint(chapter_id, data)

def is_step_done(chapter_id: str, step: str) -> bool:
    """Checks if a specific step is completed."""
    if not chapter_id:
        return False
    data = load_checkpoint(chapter_id)
    return data.get(step, False)
