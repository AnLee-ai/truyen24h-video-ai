import requests
import json

def generate_consistent_images(story_text: str, character_metadata: dict, output_dir: str):
    """
    Calls the local story_diffusion API to generate images with consistent characters.
    """
    print(f"[INFO] Routing image generation to story_diffusion API...")
    url = "http://localhost:8003/api/generate"
    payload = {
        "text": story_text,
        "characters": character_metadata,
        "output_dir": output_dir
    }
    try:
        resp = requests.post(url, json=payload, timeout=300)
        if resp.status_code == 200:
            print("[SUCCESS] story_diffusion generated images successfully.")
            return resp.json().get("image_paths", [])
        else:
            print(f"[ERROR] story_diffusion failed with status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to story_diffusion: {e}")
    
    return []
