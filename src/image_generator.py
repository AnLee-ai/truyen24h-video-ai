import os
import json
import urllib.parse
import urllib.request
import time
from src.visual_memory import ultimate_memory_50

def generate_scene_image(scene_text: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """Sinh ảnh minh họa phân cảnh 100% MIỄN PHÍ qua Pollinations.ai API đính kèm 50-Feature Memory Engine."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Biên dịch master prompt từ 50-Feature Memory Engine
    aspect = "9:16" if height > width else "16:9"
    compiled_data = ultimate_memory_50.compile_master_prompt(scene_text, target_aspect_ratio=aspect)
    prompt_str = compiled_data["positive_prompt"]
    
    print(f"[INFO] Generating Free AI Image with prompt:\n > {prompt_str[:120]}...")
    
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
            time.sleep(2)
            
    print("[ERROR] Failed to generate image via Pollinations.ai. Fallback to default background.")
    return ""

def batch_generate_scene_images(scenes: list, chapter_id: str) -> list:
    """Sinh ảnh miễn phí hàng loạt cho các cảnh của chương truyện."""
    image_paths = []
    base_dir = os.path.join("output", chapter_id, "images")
    
    for idx, scene in enumerate(scenes):
        scene_text = scene.get("text", "")
        img_file = os.path.join(base_dir, f"scene_{idx + 1:03d}.jpg")
        
        if os.path.exists(img_file) and os.path.getsize(img_file) > 1000:
            image_paths.append(img_file)
            continue
            
        img_path = generate_scene_image(scene_text, img_file)
        image_paths.append(img_path)
        
    return image_paths

if __name__ == "__main__":
    test_text = "Tiêu Viêm cầm hỏa kiếm đối đầu với kẻ thù trên đỉnh núi"
    res = generate_scene_image(test_text, "output/test_scene.jpg")
    print(f"Test image result: {res}")
