import shutil

import shutil

def call_huggingface_space(prompt: str, output_path: str) -> bool:
    try:
        from gradio_client import Client
        import shutil
        
        print(f"[INFO] Gửi lệnh sang Hugging Face Space (my-story-diffusion)...")
        # Initialize client with token
        import inspect
        kwargs = {}
        params = inspect.signature(Client.__init__).parameters
        if "token" in params:
            kwargs["token"] = os.environ.get("HF_TOKEN")
        elif "hf_token" in params:
            kwargs["hf_token"] = os.environ.get("HF_TOKEN")
        client = Client("AnLee-ai/my-story-diffusion", **kwargs)
        
        # The Gradio API accepts script_text and returns [Gallery, Log]
        result = client.predict(
            _sd_type="Unstable",
            _model_type="Only Using Textual Description",
            _upload_images=[],
            _num_steps=30,
            style_name="Japanese Anime",
            _ip_adapter_strength=0.5,
            _style_strength_ratio=20,
            guidance_scale=5,
            seed_=0,
            sa32_=0.7,
            sa64_=0.7,
            id_length_=2,
            general_prompt="",
            negative_prompt="bad anatomy, ugly, missing fingers, low res",
            prompt_array=prompt,
            g_height=1080,
            g_width=1920,
            _comic_type="No typesetting (default)",
            api_name="/process_generation"
        )
        
        if result and isinstance(result, (list, tuple)) and len(result) > 0:
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
    """GÂ»Âi Webhook lÃƒÂªn ngrok/cloudflare tunnel cÂ»Â§a Google Colab Ã„â€˜ang chÂºÂ¡y repo tÃ†Â°Ã†Â¡ng Â»Â©ng."""
    # Removed corrupted comment
    webhook_url = os.environ.get(f"COLAB_WEBHOOK_{repo_name.upper()}")
    if not webhook_url:
        return False
        
    try:
        print(f"[INFO] Gửi lệnh sang {repo_name} Webhook: {webhook_url}...")
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
    KIẾN TRÚC MEGA-PIPELINE 5 ENGINE (CLOUD/COLAB BASED)
    Mỗi ảnh sẽ được đẩy qua các tầng engine từ cao xuống thấp để đảm bảo tỷ lệ ra ảnh 100%.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if is_valid_image_file(output_path):
        print(f"[INFO] Ảnh AI đã tồn tại hợp lệ: {output_path}")
        return output_path

    # Xử lý Prompt
    clean_prompt = re.sub(r'Scene\s*\d+:', '', scene_text, flags=re.IGNORECASE).strip()
    english_prompt = clean_prompt # Trong thÂ»Â±c tÂºÂ¿ cÂºÂ§n gÂ»Âi g4f Ã„â€˜Â»Æ’ dÂ»â€¹ch, Â» Ã„â€˜ÃƒÂ¢y tÂºÂ¡m giÂºÂ£ lÂºÂ­p
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
    # ENGINE 5: Procedural Fallback Canvas (Bảo vệ tỷ lệ lỗi)
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
    print(f"[INFO] Bắt đầu sinh hàng loạt {len(scenes)} ảnh AI Mega-Pipeline (Max workers={max_workers})...")
    
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
    generate_scene_image("TiÃƒÂªu ViÃƒÂªm cÂºÂ§m hÂ»Âa kiÂºÂ¿m", "test_out.jpg")



