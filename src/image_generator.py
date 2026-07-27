import os
import json
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.visual_memory import ultimate_memory_50

def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """Sinh ảnh minh họa phân cảnh 100% MIỄN PHÍ qua Pollinations.ai API đính kèm 50-Feature Memory Engine."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    
    # 1. Biên dịch master prompt từ 50-Feature Memory Engine
    aspect = "9:16" if height > width else "16:9"
    compiled_data = ultimate_memory_50.compile_master_prompt(scene_text, target_aspect_ratio=aspect)
    prompt_str = compiled_data["positive_prompt"]
    
    print(f"[INFO] Generating Free AI Image with prompt:\n > {prompt_str[:100]}...")
    
    # 2. Định dạng URL Pollinations.ai (không tốn API key, 100% Free)
    encoded_prompt = urllib.parse.quote(prompt_str)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
    
    # 3. Tải và lưu ảnh với cơ chế Retry & Fallback
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(output_path, 'wb') as out_file:
                out_file.write(response.read())
                
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                print(f"[SUCCESS] Saved AI image: {output_path}")
                return output_path
        except Exception as e:
            print(f"[WARNING] Pollinations.ai attempt {attempt + 1} failed: {e}")
            time.sleep(1.5)
            
    print(f"[ERROR] Failed to generate image for: {output_path}")
    return ""

def batch_generate_scene_images(scenes: list, chapter_id: str, max_workers: int = 4, width: int = 1920, height: int = 1080) -> list:
    """Sinh ảnh miễn phí hàng loạt ĐA LUỒNG (Parallel ThreadPool) cho các phân cảnh (Nhanh gấp 4x)."""
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
                future = executor.submit(generate_scene_image, f"Scene {idx+1}: {scene_text}", img_file, width, height)
                tasks.append((idx, future))
                
        for idx, future in tasks:
            try:
                res_path = future.result()
                if res_path and os.path.exists(res_path):
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
