import os
import re
import urllib.parse
import requests
import time
import random
import threading
from PIL import Image, ImageDraw
import shutil

# Global Circuit Breaker State
_hf_consecutive_failures = 0
_hf_circuit_open = False
_hf_circuit_opened_at = 0.0
_hf_lock = threading.Lock()

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

def call_huggingface_space(prompt: str, output_path: str) -> bool:
    global _hf_consecutive_failures, _hf_circuit_open, _hf_circuit_opened_at
    
    if _hf_circuit_open:
        if time.time() - _hf_circuit_opened_at > 300:
            print("[CIRCUIT BREAKER] 🟡 Thời gian làm mát (5 phút) đã hết. Thử kết nối lại với Engine 1 (Half-Open)...")
            _hf_circuit_open = False
            _hf_consecutive_failures = 2
        else:
            remaining = int(300 - (time.time() - _hf_circuit_opened_at))
            print(f"[CIRCUIT BREAKER] 🔴 Engine 1 đang bị ngắt (Chờ {remaining}s nữa để thử lại). Chuyển tải sang Engine tiếp theo...")
            return False

    with _hf_lock:
        print(f"[ENGINE 1] 🚀 Bắt đầu gọi FLUX.1-schnell trên Hugging Face Space...")
        from gradio_client import Client
        import time, random
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                try:
                    client = Client("black-forest-labs/FLUX.1-schnell", hf_token=os.environ.get("HF_TOKEN"))
                except TypeError as e:
                    if "unexpected keyword argument" in str(e):
                        client = Client("black-forest-labs/FLUX.1-schnell", token=os.environ.get("HF_TOKEN"))
                    else:
                        raise
                
                result, _ = client.predict(
                    prompt=prompt,
                    seed=0,
                    randomize_seed=True,
                    width=1024,
                    height=1024,
                    num_inference_steps=4,
                    api_name="/infer"
                )
                
                if result and isinstance(result, dict):
                    img_path = result.get('path', '')
                    import shutil
                    if img_path and os.path.exists(img_path):
                        shutil.copy(img_path, output_path)
                        _hf_consecutive_failures = 0
                        print(f"[ENGINE 1] 🟢 Thành công ở lần thử {attempt}/{max_retries}!")
                        return True
                raise ValueError("Kết quả API rỗng hoặc không chứa ảnh hợp lệ.")
                
            except Exception as e:
                err_msg = str(e)
                print(f"[ENGINE 1] ⚠️ Lỗi ở lần thử {attempt}/{max_retries}: {err_msg}")
                
                if attempt < max_retries:
                    sleep_time = (2 ** attempt) * 3 + random.uniform(2, 7)
                    print(f"[ENGINE 1] ⏳ Kích hoạt Jitter Sleep: Đang chờ {sleep_time:.1f} giây để lách Rate Limit...")
                    import time
                    time.sleep(sleep_time)
                else:
                    _hf_consecutive_failures += 1
                    if _hf_consecutive_failures >= 3:
                        _hf_circuit_open = True
                        _hf_circuit_opened_at = time.time()
                        print(f"[CIRCUIT BREAKER] 🔴 Quá nhiều lỗi liên tiếp ({_hf_consecutive_failures}). Engine 1 ngắt kết nối trong 5 phút!")
                    print("[ENGINE 1] ❌ HF Space thất bại hoàn toàn.")
                    return False
    return False
def call_colab_webhook(prompt: str, output_path: str, repo_name: str, width: int, height: int) -> bool:
    webhook_url = os.environ.get(f"COLAB_WEBHOOK_{repo_name.upper()}")
    if not webhook_url:
        return False
        
    try:
        print(f"[INFO] Gửi lệnh sang {repo_name} Webhook: {webhook_url}...")
        payload = {"prompt": prompt, "width": width, "height": height}
        resp = requests.post(webhook_url, json=payload, timeout=60)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return is_valid_image_file(output_path)
    except Exception as e:
        print(f"[WARNING] Webhook {repo_name} failed: {e}")
    return False

def call_flux_pollinations(prompt: str, output_path: str, width: int, height: int, seed: int) -> bool:
    print("[ENGINE 4] 🚀 Bắt đầu gọi FLUX.1 (Pollinations API)...")
    encoded_prompt = urllib.parse.quote(prompt)
    get_url_flux = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux-anime&seed={seed}&nologo=true"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(get_url_flux, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                if is_valid_image_file(output_path):
                    size_kb = len(resp.content) / 1024
                    print(f"[ENGINE 4] 🟢 Tải ảnh thành công từ FLUX. Dung lượng: {size_kb:.1f} KB.")
                    return True
            print(f"[ENGINE 4] ⚠️ Lỗi HTTP {resp.status_code} hoặc file quá nhỏ (<10KB).")
        except Exception as e:
            print(f"[ENGINE 4] ⚠️ Lỗi ở lần thử {attempt}/{max_retries}: {e}")
            
        if attempt < max_retries:
            sleep_time = random.uniform(5, 10)
            print(f"[ENGINE 4] ⏳ Đang chờ {sleep_time:.1f} giây trước khi gọi lại FLUX...")
            time.sleep(sleep_time)
            
    print("[ENGINE 4] ❌ FLUX.1 thất bại hoàn toàn.")
    return False

def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080, seed: int = None) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if is_valid_image_file(output_path):
        print(f"[INFO] Ảnh AI đã tồn tại hợp lệ: {output_path}")
        return output_path

    clean_prompt = re.sub(r'Scene\s*\d+:', '', scene_text, flags=re.IGNORECASE).strip()
    english_prompt = clean_prompt 
    base_seed = seed if seed is not None else random.randint(1, 999999999)
    
    # ENGINE 1: Hugging Face (Protected by Lock & Circuit Breaker)
    if call_huggingface_space(english_prompt, output_path):
        print(f"[SUCCESS] Saved AI Image via Engine 1 (Hugging Face ZeroGPU): {output_path}")
        return output_path
        
    # ENGINE 2: Fooocus
    if call_colab_webhook(english_prompt, output_path, "FOOOCUS", width, height):
        print(f"[SUCCESS] Saved AI Image via Engine 2 (Fooocus Colab): {output_path}")
        return output_path

    # ENGINE 3: IP-Adapter
    if call_colab_webhook(english_prompt, output_path, "CONTROLNET_IPADAPTER", width, height):
        print(f"[SUCCESS] Saved AI Image via Engine 3 (ControlNet + IP-Adapter Colab): {output_path}")
        return output_path

    # ENGINE 4: FLUX.1 Pollinations
    if call_flux_pollinations(english_prompt, output_path, width, height, base_seed):
        print(f"[SUCCESS] Saved AI Image via Engine 4 (FLUX.1 API): {output_path}")
        return output_path

    # ENGINE 5: Procedural Fallback (Bảo vệ tỷ lệ lỗi)
    try:
        print("[ENGINE 5] ⚠️ Tất cả các AI Engines đều sập! Kích hoạt thuật toán vẽ Canvas dự phòng...")
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


def chunk_scene_prompts(prompts: list, size: int = 5):
    for i in range(0, len(prompts), size):
        yield prompts[i:i + size]

def call_story_diffusion_batch(general_prompt: str, prompt_array_list: list, start_idx: int, base_dir: str, width: int = 768, height: int = 768) -> list:
    global _hf_consecutive_failures, _hf_circuit_open, _hf_circuit_opened_at
    
    if _hf_circuit_open:
        if time.time() - _hf_circuit_opened_at > 300:
            _hf_circuit_open = False
            _hf_consecutive_failures = 2
        else:
            return []

    with _hf_lock:
        print(f"[ENGINE 1 - BATCH] 🚀 Gọi Story Diffusion (Batch từ {start_idx+1} đến {start_idx+len(prompt_array_list)})...")
        from gradio_client import Client
        import shutil
        
        prompt_text = "\n".join(prompt_array_list)
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                try:
                    client = Client("AnLee-ai/my-story-diffusion", hf_token=os.environ.get("HF_TOKEN"))
                except TypeError as e:
                    if "unexpected keyword argument" in str(e):
                        client = Client("AnLee-ai/my-story-diffusion", token=os.environ.get("HF_TOKEN"))
                    else:
                        raise
                
                result = client.predict(
                    None,
                    20,
                    "Japanese Anime",
                    1,
                    0,
                    general_prompt,
                    "bad quality, blurry, deformed, poorly drawn, extra limbs, ugly, text, watermark",
                    prompt_text,
                    height,
                    width,
                    "No typesetting (default)",
                    api_name="/process_generation"
                )
                
                if result and isinstance(result, list):
                    generated_files = []
                    for i, img_dict in enumerate(result):
                        if i >= len(prompt_array_list):
                            break
                        img_path = img_dict.get('image', '') if isinstance(img_dict, dict) else img_dict
                        if img_path and os.path.exists(img_path):
                            target_file = os.path.join(base_dir, f"scene_{start_idx + i + 1:03d}.jpg")
                            shutil.copy(img_path, target_file)
                            generated_files.append((start_idx + i, target_file))
                    
                    if generated_files:
                        _hf_consecutive_failures = 0
                        print(f"[ENGINE 1 - BATCH] 🟢 Thành công tạo {len(generated_files)} ảnh từ Story Diffusion!")
                        return generated_files
                raise ValueError("Kết quả API rỗng hoặc không đúng định dạng Gallery.")
                
            except Exception as e:
                err_msg = str(e)
                print(f"[ENGINE 1 - BATCH] ⚠️ Lỗi ở lần thử {attempt}/{max_retries}: {err_msg}")
                if attempt < max_retries:
                    time.sleep(10)
                else:
                    _hf_consecutive_failures += 1
                    if _hf_consecutive_failures >= 2:
                        _hf_circuit_open = True
                        _hf_circuit_opened_at = time.time()
                        print(f"[CIRCUIT BREAKER] 🔴 Story Diffusion bị ngắt kết nối.")
                    return []
    return []


def batch_generate_scene_images(scenes: list, chapter_id: str, max_workers: int = 2, width: int = 1920, height: int = 1080) -> list:
    base_dir = os.path.join("output", chapter_id, "images")
    os.makedirs(base_dir, exist_ok=True)
    
    import src.database as db
    novel_id = db.get_novel_id_from_chapter(chapter_id)
    novel = db.get_novel(novel_id)
    protagonist = novel.get("protagonist", {}) if novel else {}
    general_prompt = protagonist.get("appearance", "")
    if not general_prompt:
        general_prompt = "1boy, solo, detailed, masterpiece, high quality" 
        
    image_map = {}
    print(f"[INFO] Bắt đầu sinh hàng loạt {len(scenes)} ảnh AI Mega-Pipeline (Tối ưu Batch Story Diffusion)...")
    
    # 1. Story Diffusion Batching
    chunk_size = 5
    scene_chunks = list(chunk_scene_prompts(scenes, chunk_size))
    failed_indices = []
    
    for i, chunk in enumerate(scene_chunks):
        start_idx = i * chunk_size
        print(f"--- Xử lý Batch {i+1}/{len(scene_chunks)} (Scenes {start_idx+1} to {start_idx+len(chunk)}) ---")
        generated = call_story_diffusion_batch(general_prompt, chunk, start_idx, base_dir, width=1024, height=768)
        
        generated_idxs = set()
        if generated:
            for idx, path in generated:
                image_map[idx] = path
                generated_idxs.add(idx)
                
        for j in range(len(chunk)):
            if (start_idx + j) not in generated_idxs:
                failed_indices.append((start_idx + j, chunk[j]))
                
    # 2. Fallback cho các ảnh thất bại
    if failed_indices:
        print(f"[INFO] Có {len(failed_indices)} ảnh thất bại từ Story Diffusion. Chuyển sang Fallback (FLUX/Pollinations)...")
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
            futures = {executor.submit(_gen_single_scene, item): item[0] for item in failed_indices}
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
    generate_scene_image("Tiêu Viêm cầm hỏa kiếm", "test_out.jpg")
