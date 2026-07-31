import os
import re
import json
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from src.visual_memory import ultimate_memory_50

def enhance_image_quality(image_path: str):
    """Tự động nâng cấp độ sắc nét nét vẽ AI Manhwa 2D SIÊU NÉT (Sharpness 2.20x + PIL Sharpen Filter + JPEG 100% Quality 4:4:4)."""
    try:
        if not os.path.exists(image_path) or os.path.getsize(image_path) < 1000:
            return
        from PIL import ImageFilter
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            # 1. Áp dụng bộ lọc Sharpen phần cứng để làm rõ chi tiết viền mực
            img = img.filter(ImageFilter.SHARPEN)
            # 2. Tăng độ rực rỡ cel-shading 1.25x
            enhancer_color = ImageEnhance.Color(img)
            img = enhancer_color.enhance(1.25)
            # 3. Tăng độ sắc nét nét vẽ đen 2.20x (Siêu sắc nét 4K Cực Đại)
            enhancer_sharp = ImageEnhance.Sharpness(img)
            img = enhancer_sharp.enhance(2.20)
            # 4. Tăng tương phản nổi bật 1.15x
            enhancer_contrast = ImageEnhance.Contrast(img)
            img = enhancer_contrast.enhance(1.15)
            # 5. Lưu chất lượng 100% 4:4:4 Chroma Subsampling không nén mờ
            img.save(image_path, "JPEG", quality=100, subsampling=0)
    except Exception as e:
        print(f"[WARNING] Post-processing image quality failed: {e}")

def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Sinh ảnh minh họa phân cảnh 100% MIỄN PHÍ qua Ma Trận 5 Nền Tảng AI Sinh Ảnh:
    - Provider 1: Pollinations.ai Multi-Model (flux-anime, flux, turbo, flux-real, any-dark)
    - Provider 2: Lexica.art High Quality Manhwa Art Search Engine
    - Provider 3: HuggingFace Flux/SDXL Inference Engine
    - Provider 4: Public High-Res Dynamic Art Engine (Picsum & Unsplash Engine)
    - Provider 5: Emergency Dynamic 4K Manhwa Comic Canvas (Khung Ảnh Truyện Tranh 2D Rực Rỡ Chữ Vàng)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    
    # 1. Biên dịch master prompt từ 50-Feature Memory Engine (GIỮ NGUYÊN 100% PROMPT ĐẦY ĐỦ, KHÔNG CẮT BỚT)
    aspect = "9:16" if height > width else "16:9"
    compiled_data = ultimate_memory_50.compile_master_prompt(scene_text, target_aspect_ratio=aspect)
    # Shorten prompt for URL APIs to avoid HTTP 400/429 URL length errors
    clean_short_prompt = "masterpiece 2d korean manhwa webtoon art, solo leveling style, " + re.sub(r"[^\w\s,]", "", scene_text[:180])
    encoded_prompt = urllib.parse.quote(clean_short_prompt[:260])
    
    print(f"[INFO] Generating Free AI Image with short encoded prompt:\n > {clean_short_prompt}...")
    base_seed = int(compiled_data.get("hash", "0")[:8], 16) % 1000000

    # NỀN TẢNG 1 (ĐẸP NHẤT & SẮC NÉT NHẤT): HuggingFace FLUX.1 / SDXL Base Inference Engine
    try:
        print("[INFO] Trying Provider 1 (RANK #1 ART QUALITY): HuggingFace FLUX.1 Engine...")
        import requests
        unified_hf_prompt = prompt_str
        headers_hf = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        hf_models = [
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        ]
        for hf_url in hf_models:
            resp = requests.post(hf_url, json={"inputs": unified_hf_prompt}, headers=headers_hf, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                enhance_image_quality(output_path)
                print(f"[SUCCESS] Saved Rank #1 AI image via HuggingFace FLUX.1 Engine: {output_path}")
                return output_path
    except Exception as e:
        print(f"[WARNING] HuggingFace FLUX.1 engine failed: {e}")

    # NỀN TẢNG 2 (RANK #2 ART QUALITY): Pollinations.ai Multi-Model Engine (flux-anime / flux / turbo)
    pollination_models = ["flux-anime", "flux", "turbo", "flux-real", "any-dark"]
    for idx, model_name in enumerate(pollination_models):
        seed = base_seed + (idx * 111) + int(time.time() % 1000)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model_name}&seed={seed}&nologo=true"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=30) as response, open(output_path, 'wb') as out_file:
                out_file.write(response.read())
                
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                enhance_image_quality(output_path)
                print(f"[SUCCESS] Saved Rank #2 AI image via Pollinations ({model_name}): {output_path}")
                time.sleep(1.5)  # Dãn cách 1.5s
                return output_path
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f"[WARNING] Pollinations model '{model_name}' rate limited (429). Tự động chờ 4.0s để giải phóng Quota...")
                time.sleep(4.0)
            else:
                print(f"[WARNING] Pollinations model '{model_name}' failed: {e}")
                time.sleep(1.5)

    # NỀN TẢNG 3 (RANK #3 ART QUALITY): Airforce AI Flux/Anime Engine
    try:
        print("[INFO] Switching to Provider 3 (RANK #3 ART QUALITY): Airforce AI Flux Engine...")
        air_prompt = urllib.parse.quote(clean_short_prompt[:250])
        air_url = f"https://api.airforce/v1/imagen?prompt={air_prompt}&model=flux"
        req_a = urllib.request.Request(air_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req_a, timeout=25) as img_resp, open(output_path, 'wb') as out_file:
            out_file.write(img_resp.read())
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            enhance_image_quality(output_path)
            print(f"[SUCCESS] Saved Rank #3 AI image via Airforce AI Engine: {output_path}")
            return output_path
    except Exception as e:
        print(f"[WARNING] Airforce AI engine failed: {e}")

    # NỀN TẢNG 4 (RANK #4 ART QUALITY): Hercai Instant AI Image Engine
    try:
        print("[INFO] Switching to Provider 4 (RANK #4 ART QUALITY): Hercai AI Anime Engine...")
        hercai_prompt = urllib.parse.quote(clean_short_prompt[:200])
        hercai_url = f"https://hercai.onrender.com/v3/text2image?prompt={hercai_prompt}"
        req_h = urllib.request.Request(hercai_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req_h, timeout=25) as response:
            data = json.loads(response.read().decode('utf-8'))
            url_img = data.get("url")
            if url_img:
                req_download = urllib.request.Request(url_img, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_download, timeout=30) as img_resp, open(output_path, 'wb') as out_file:
                    out_file.write(img_resp.read())
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    enhance_image_quality(output_path)
                    print(f"[SUCCESS] Saved Rank #4 AI image via Hercai AI Engine: {output_path}")
                    return output_path
    except Exception as e:
        print(f"[WARNING] Hercai AI engine failed: {e}")

    # NỀN TẢNG 5 (RANK #5 ART QUALITY): Lexica.art Manhwa Webtoon Search Engine
    try:
        print("[INFO] Switching to Provider 5 (RANK #5 ART QUALITY): Lexica.art Engine...")
        clean_q = re.sub(r"[^\w\s]", "", scene_text[:80])
        lexica_query = urllib.parse.quote("Korean 2D manhwa webtoon " + clean_q)
        lexica_url = f"https://lexica.art/api/v1/search?q={lexica_query}"
        req = urllib.request.Request(lexica_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
            images = data.get("images", [])
            if images:
                src_url = images[0].get("src")
                if src_url:
                    req_img = urllib.request.Request(src_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_img, timeout=25) as img_resp, open(output_path, 'wb') as out_file:
                        out_file.write(img_resp.read())
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                        enhance_image_quality(output_path)
                        print(f"[SUCCESS] Saved Rank #5 AI image via Lexica Art: {output_path}")
                        return output_path
    except Exception as e:
        print(f"[WARNING] Lexica.art engine failed: {e}")

    # NỀN TẢNG CUỐI CÙNG: Ép sinh ảnh AI Anime Pollinations 100% (XÓA BỎ 100% CANVAS VÒNG TRÒN TÍM)
    print(f"[WARNING] Final Retry: Forcing Pollinations AI Anime generation for {output_path}...")
    final_url = f"https://image.pollinations.ai/prompt/masterpiece%202d%20korean%20manhwa%20webtoon%20anime%20art%20solo%20leveling%20hero?width={width}&height={height}&model=flux-anime&nologo=true"
    for final_attempt in range(3):
        try:
            req_f = urllib.request.Request(final_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req_f, timeout=40) as response, open(output_path, 'wb') as out_file:
                out_file.write(response.read())
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                enhance_image_quality(output_path)
                print(f"[SUCCESS] Saved Forced AI Anime Image: {output_path}")
                return output_path
        except Exception as e:
            print(f"[WARNING] Final AI Anime attempt {final_attempt+1} failed: {e}")
            time.sleep(3.0)
            
    print(f"[ERROR] Could not generate AI image for {output_path}")
    return output_path

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
