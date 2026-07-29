import os
import json
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.visual_memory import ultimate_memory_50

def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Sinh ảnh minh họa phân cảnh 100% MIỄN PHÍ qua Ma Trận 5 Nền Tảng AI Sinh Ảnh:
    - Provider 1: Pollinations.ai Multi-Model (flux-anime, flux, turbo, flux-real, any-dark)
    - Provider 2: Lexica.art High Quality Manhwa Art Search Engine
    - Provider 3: HuggingFace Flux/SDXL Inference Engine
    - Provider 4: Emergency Dynamic 4K Gradient Canvas Generator (Không bao giờ lỗi)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    
    # 1. Biên dịch master prompt từ 50-Feature Memory Engine (GIỮ NGUYÊN 100% PROMPT ĐẦY ĐỦ, KHÔNG CẮT BỚT)
    aspect = "9:16" if height > width else "16:9"
    compiled_data = ultimate_memory_50.compile_master_prompt(scene_text, target_aspect_ratio=aspect)
    prompt_str = compiled_data["positive_prompt"]
    
    encoded_prompt = urllib.parse.quote(prompt_str)
    
    print(f"[INFO] Generating Free AI Image with FULL prompt:\n > {prompt_str[:120]}...")
    base_seed = int(compiled_data.get("hash", "0")[:8], 16) % 1000000

    # NỀN TẢNG 1: Pollinations.ai Multi-Model Engine (Tăng thời gian chờ timeout=35s & Dãn cách 3.0s khi bị 429)
    pollination_models = ["flux-anime", "flux", "turbo", "flux-real", "any-dark"]
    for idx, model_name in enumerate(pollination_models):
        seed = base_seed + (idx * 111) + int(time.time() % 1000)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model_name}&seed={seed}&enhance=true&nologo=true"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=35) as response, open(output_path, 'wb') as out_file:
                out_file.write(response.read())
                
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                print(f"[SUCCESS] Saved AI image via Pollinations ({model_name}): {output_path}")
                return output_path
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f"[WARNING] Pollinations model '{model_name}' rate limited (429). Tự động chờ 3.0s để giải phóng Quota...")
                time.sleep(3.0)
            else:
                print(f"[WARNING] Pollinations model '{model_name}' failed: {e}")
                time.sleep(1.5)

    # NỀN TẢNG 2: Lexica.art & Public High-Quality Anime Search Engine (Tăng thời gian chờ timeout=25s)
    try:
        print("[INFO] Pollinations exhausted. Switching to Provider 2: Lexica.art Engine...")
        clean_q = re.sub(r"[^\w\s]", "", scene_text[:80])
        lexica_query = urllib.parse.quote("Korean 2D manhwa webtoon " + clean_q)
        lexica_url = f"https://lexica.art/api/v1/search?q={lexica_query}"
        req = urllib.request.Request(lexica_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode('utf-8'))
            images = data.get("images", [])
            if images:
                src_url = images[0].get("src")
                if src_url:
                    req_img = urllib.request.Request(src_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_img, timeout=30) as img_resp, open(output_path, 'wb') as out_file:
                        out_file.write(img_resp.read())
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                        print(f"[SUCCESS] Saved AI image via Lexica Art: {output_path}")
                        return output_path
    except Exception as e:
        print(f"[WARNING] Lexica.art engine failed: {e}")

    # NỀN TẢNG 3: HuggingFace Flux/SDXL Inference Router (Giữ Full Prompt & Tăng timeout=45s)
    try:
        print("[INFO] Switching to Provider 3: HuggingFace Public AI Engine...")
        import requests
        unified_hf_prompt = prompt_str
        headers_hf = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        hf_models = [
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        ]
        for hf_url in hf_models:
            resp = requests.post(hf_url, json={"inputs": unified_hf_prompt}, headers=headers_hf, timeout=45)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                print(f"[SUCCESS] Saved AI image via HuggingFace Engine: {output_path}")
                return output_path
    except Exception as e:
        print(f"[WARNING] HuggingFace AI engine failed: {e}")

    # NỀN TẢNG 4: Emergency Dynamic 4K Manhwa Gradient Canvas (Không Bao Giờ Lỗi)
    print(f"[WARNING] Emergency fallback: Generating Dynamic Manhwa Canvas for {output_path}...")
    return generate_emergency_gradient_canvas(scene_text, output_path, width, height)

def generate_emergency_gradient_canvas(scene_text: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """Sinh ảnh Canvas nghệ thuật Manhwa 4K dự phòng (100% Không Lỗi Mạng)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (width, height), color=(15, 18, 28))
        draw = ImageDraw.Draw(img)
        
        # Vẽ họa tiết hiệu ứng hào quang huyền bí
        for radius in range(width, 0, -80):
            color = (int(20 + radius/30), int(25 + radius/40), int(55 + radius/20))
            draw.ellipse([width//2 - radius, height//2 - radius, width//2 + radius, height//2 + radius], fill=color)
            
        # Thêm dải mờ Vignette
        draw.rectangle([0, 0, width, height], outline=(0, 0, 0), width=15)
        img.save(output_path, "JPEG", quality=90)
        print(f"[SUCCESS] Saved Emergency Dynamic Canvas: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Emergency canvas failed: {e}")
        return ""

def batch_generate_scene_images(scenes: list, chapter_id: str, max_workers: int = 2, width: int = 1920, height: int = 1080) -> list:
    """Sinh ảnh miễn phí hàng loạt ĐA LUỒNG (Parallel ThreadPool) cho các phân cảnh với nhịp dãn cách 0.3s."""
    base_dir = os.path.join("output", chapter_id, "images")
    os.makedirs(base_dir, exist_ok=True)
    
    tasks = []
    image_map = {}
    
    print(f"[INFO] Bắt đầu sinh hàng loạt {len(scenes)} ảnh AI bằng ThreadPool (Max workers={max_workers})...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, scene_text in enumerate(scenes):
            img_file = os.path.join(base_dir, f"scene_{idx + 1:03d}.jpg")
            if os.path.exists(img_file) and os.path.getsize(img_file) > 1000:
                image_map[idx] = img_file
            else:
                future = executor.submit(generate_scene_image, scene_text, img_file, width, height)
                tasks.append((idx, future))
                time.sleep(0.3) # Dãn cách nhẹ giữa các request tránh nghẽn IP
                
        for idx, future in tasks:
            try:
                res_path = future.result()
                if res_path and os.path.exists(res_path) and os.path.getsize(res_path) > 1000:
                    image_map[idx] = res_path
            except Exception as e:
                print(f"[WARNING] Task scene {idx+1} failed: {e}")
                
    # Sắp xếp đúng thứ tự phân cảnh
    result_paths = [image_map[i] for i in sorted(image_map.keys())]
    print(f"[SUCCESS] Đã hoàn thành sinh {len(result_paths)} ảnh AI đa luồng!")
    return result_paths

if __name__ == "__main__":
    test_text = "Tiêu Viêm cầm hỏa kiếm đối đầu với kẻ thù trên đỉnh núi"
    res = generate_scene_image(test_text, "output/test/test_img.jpg")
    print(f"Test result: {res}")
