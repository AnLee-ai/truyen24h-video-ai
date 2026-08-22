import shutil

import shutil

def call_huggingface_space(prompt: str, output_path: str) -> bool:
    try:
        from gradio_client import Client
        import shutil
        
        print(f"[INFO] Gửi lệnh sang Hugging Face Space (ZeroGPU)...")
        # Initialize client with token
        client = Client("AnLee-ai/truyen24h-video-ai", hf_token=os.environ.get("HF_TOKEN"))
        
        # The Gradio API accepts script_text and returns [Gallery, Log]
        result = client.predict(
            script_text=prompt,
            api_name="/predict"
        )
        
        if result and isinstance(result, (list, tuple)) and result[0]:
            gallery = result[0]
            if isinstance(gallery, list) and len(gallery) > 0:
                first_img = gallery[0]
                img_path = first_img.get('image', '') if isinstance(first_img, dict) else first_img
                if img_path and os.path.exists(img_path):
                    shutil.copy(img_path, output_path)
                    return True
        return False
    except Exception as e:
        print(f"[WARNING] Hugging Face Space failed: {e}")
        return False
import os
import re
import urllib.parse
import requests
from PIL import Image, ImageDraw
import random
def is_valid_image_file(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    if os.path.getsize(file_path) < 5000:
        return False
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def call_colab_webhook(prompt: str, output_path: str, repo_name: str, width: int, height: int) -> bool:
    """GÃ¡Â»Âi Webhook lÃƒÂªn ngrok/cloudflare tunnel cÃ¡Â»Â§a Google Colab Ã„â€˜ang chÃ¡ÂºÂ¡y repo tÃ†Â°Ã†Â¡ng Ã¡Â»Â©ng."""
    # GiÃ¡ÂºÂ£ lÃ¡ÂºÂ­p Ã„â€˜Ã¡Â»Âc Colab Webhook URL tÃ¡Â»Â« biÃ¡ÂºÂ¿n mÃƒÂ´i trÃ†Â°Ã¡Â»Âng
    webhook_url = os.environ.get(f"COLAB_WEBHOOK_{repo_name.upper()}")
    if not webhook_url:
        return False
        
    try:
        print(f"[INFO] GÃ¡Â»Â­i lÃ¡Â»â€¡nh sang {repo_name} Webhook: {webhook_url}...")
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height
        }
        resp = requests.post(webhook_url, json=payload, timeout=60)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return is_valid_image_file(output_path)
    except Exception as e:
        print(f"[WARNING] Webhook {repo_name} failed: {e}")
    return False


def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080, seed: int = None) -> str:
    """
    KIÃ¡ÂºÂ¾N TRÃƒÅ¡C MEGA-PIPELINE 5 ENGINE (CLOUD/COLAB BASED)
    MÃ¡Â»â€”i Ã¡ÂºÂ£nh sÃ¡ÂºÂ½ Ã„â€˜Ã†Â°Ã¡Â»Â£c Ã„â€˜Ã¡ÂºÂ©y qua cÃƒÂ¡c tÃ¡ÂºÂ§ng engine tÃ¡Â»Â« cao xuÃ¡Â»â€˜ng thÃ¡ÂºÂ¥p Ã„â€˜Ã¡Â»Æ’ Ã„â€˜Ã¡ÂºÂ£m bÃ¡ÂºÂ£o tÃ¡Â»Â· lÃ¡Â»â€¡ ra Ã¡ÂºÂ£nh 100%.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if is_valid_image_file(output_path):
        print(f"[INFO] Ã¡ÂºÂ¢nh AI Ã„â€˜ÃƒÂ£ tÃ¡Â»â€œn tÃ¡ÂºÂ¡i hÃ¡Â»Â£p lÃ¡Â»â€¡: {output_path}")
        return output_path

    # XÃ¡Â»Â­ lÃƒÂ½ Prompt
    clean_prompt = re.sub(r'Scene\s*\d+:', '', scene_text, flags=re.IGNORECASE).strip()
    english_prompt = clean_prompt # Trong thÃ¡Â»Â±c tÃ¡ÂºÂ¿ cÃ¡ÂºÂ§n gÃ¡Â»Âi g4f Ã„â€˜Ã¡Â»Æ’ dÃ¡Â»â€¹ch, Ã¡Â»Å¸ Ã„â€˜ÃƒÂ¢y tÃ¡ÂºÂ¡m giÃ¡ÂºÂ£ lÃ¡ÂºÂ­p
    base_seed = seed if seed is not None else random.randint(1, 999999999)
    
    # =========================================================================
    # ENGINE 1: Mangstoon Story AI via Hugging Face Space (ZeroGPU)
    # =========================================================================
    if call_huggingface_space(english_prompt, output_path):
        print(f"[SUCCESS] Saved AI Image via Engine 1 (Hugging Face ZeroGPU): {output_path}")
        return output_path
        
    # =========================================================================
    # ENGINE 2: Fooocus (Artistic) via Colab Webhook
    # =========================================================================
    if call_colab_webhook(english_prompt, output_path, "FOOOCUS", width, height):
        print(f"[SUCCESS] Saved AI Image via Engine 2 (Fooocus Colab): {output_path}")
        return output_path

    # =========================================================================
    # ENGINE 3: IP-Adapter (Style Clone) & ControlNet (Pose) via Colab Webhook
    # =========================================================================
    if call_colab_webhook(english_prompt, output_path, "CONTROLNET_IPADAPTER", width, height):
        print(f"[SUCCESS] Saved AI Image via Engine 3 (ControlNet + IP-Adapter Colab): {output_path}")
        return output_path

    # =========================================================================
    # ENGINE 4: FLUX.1 (HuggingFace Inference API / Pollinations GET)
    # =========================================================================
    try:
        encoded_prompt = urllib.parse.quote(english_prompt)
        get_url_flux = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux-anime&seed={base_seed}&nologo=true"
        req = urllib.request.Request(get_url_flux, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            image_data = response.read()
            if len(image_data) > 10000:
                with open(output_path, "wb") as f:
                    f.write(image_data)
                if is_valid_image_file(output_path):
                    print(f"[SUCCESS] Saved AI Image via Engine 4 (FLUX.1 API): {output_path}")
                    return output_path
    except Exception as e:
        print(f"[WARNING] Engine 4 (FLUX.1) failed: {e}")

    # =========================================================================
    # ENGINE 5: Procedural Fallback Canvas (BÃ¡ÂºÂ£o vÃ¡Â»â€¡ tÃ¡Â»Â· lÃ¡Â»â€¡ lÃ¡Â»â€”i)
    # =========================================================================
    try:
        img = Image.new('RGB', (width, height), color=(15, 20, 35))
        draw = ImageDraw.Draw(img)
        seed_num = base_seed
        r_theme = (seed_num * 13) % 150 + 20
        g_theme = (seed_num * 29) % 150 + 30
        b_theme = (seed_num * 43) % 180 + 70
        
        for y in range(height):
            ratio = y / height
            r = int(15 * (1 - ratio) + r_theme * ratio * 0.5)
            g = int(20 * (1 - ratio) + g_theme * ratio * 0.5)
            b = int(45 * (1 - ratio) + b_theme * ratio * 0.7)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        img.save(output_path, 'JPEG', quality=95)
        print(f"[SUCCESS] Generated 2D Procedural Fallback Canvas: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Procedural Webtoon renderer failed: {e}")

    return output_path

def batch_generate_scene_images(scenes: list, chapter_id: str, max_workers: int = 5, width: int = 1920, height: int = 1080) -> list:
    base_dir = os.path.join("output", chapter_id, "images")
    os.makedirs(base_dir, exist_ok=True)
    
    image_map = {}
    print(f"[INFO] BÃ¡ÂºÂ¯t Ã„â€˜Ã¡ÂºÂ§u sinh hÃƒÂ ng loÃ¡ÂºÂ¡t {len(scenes)} Ã¡ÂºÂ£nh AI Mega-Pipeline (Max workers={max_workers})...")
    
    import concurrent.futures
    def _gen_single_scene(item):
        idx, scene_text = item
        img_file = os.path.join(base_dir, f"scene_{idx + 1:03d}.jpg")
        try:
            res_p = generate_scene_image(scene_text, img_file, width, height)
            if is_valid_image_file(res_p):
                return idx, res_p
        except Exception as e:
            print(f"[WARNING] Task scene {idx+1} failed: {e}")
        return idx, ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        items = list(enumerate(scenes))
        futures = {executor.submit(_gen_single_scene, item): item[0] for item in items}
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, res_p = future.result()
                if res_p and is_valid_image_file(res_p):
                    image_map[idx] = res_p
            except Exception:
                pass

    result_paths = [image_map[i] for i in sorted(image_map.keys())]
    return result_paths

if __name__ == "__main__":
    generate_scene_image("TiÃƒÂªu ViÃƒÂªm cÃ¡ÂºÂ§m hÃ¡Â»Âa kiÃ¡ÂºÂ¿m", "test_out.jpg")



