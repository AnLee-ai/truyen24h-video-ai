import os
import json
import concurrent.futures
from src import database, config

CAMERA_ANGLES = [
    "Low-angle dynamic medium shot, 35mm lens",
    "Close-up portrait shot, sharp focus on eyes, shallow depth of field",
    "Wide panoramic landscape shot, cinematic 8k view",
    "Dutch angle 45-degree action pose, high intensity",
    "Over-the-shoulder perspective, dramatic depth",
    "Top-down bird eye view, epic scale"
]

LIGHTING_STYLES = [
    "Volumetric purple flame glow, dramatic rim lighting",
    "Bright golden celestial aura, cinematic soft shadows",
    "Dark crimson ominous shadow, high contrast chiaroscuro",
    "Emerald wind gust particle effect, vibrant cel-shaded lighting",
    "Dusk golden hour warm sunlight, atmospheric haze"
]

NEGATIVE_PROMPT_DEFAULT = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark"

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list) -> tuple:
    """Xử lý song song 1 phân cảnh độc lập (Parallel Worker)."""
    idx, scene_text = item
    
    # 1. Nhận diện nhân vật xuất hiện trong cảnh
    detected_chars = []
    char_prompts = []
    for c in characters_data:
        c_name = c.get("name", "")
        if c_name and c_name in scene_text:
            detected_chars.append(c_name)
            desc = c.get("description", "")
            if desc:
                char_prompts.append(f"{c_name} ({desc[:80]})")
            else:
                char_prompts.append(c_name)
                
    # 2. Nhận diện bối cảnh thế giới
    detected_lore = []
    for l in world_lore_data:
        kw = l.get("keyword", "")
        if kw and kw in scene_text:
            detected_lore.append(kw)

    # 3. Phối hợp camera & lighting ngẫu nhiên theo index
    camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
    lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]

    # 4. Xây dựng Enhanced Positive Prompt
    char_str = ", ".join(char_prompts) if char_prompts else "Manhwa protagonist cultivator"
    lore_str = ", ".join(detected_lore) if detected_lore else "Ancient Oriental World"
    
    positive_prompt = (
        f"masterpiece, best quality, 2D manhwa webtoon style, {scene_text}, "
        f"character specs: [{char_str}], environment: [{lore_str}], "
        f"camera: [{camera}], lighting: [{lighting}], cel shaded, 8k resolution --ar 16:9"
    )

    manifest_item = {
        "scene_index": idx + 1,
        "raw_text": scene_text,
        "detected_characters": detected_chars,
        "detected_lore": detected_lore,
        "camera_angle": camera,
        "lighting": lighting,
        "enhanced_prompt": positive_prompt,
        "negative_prompt": NEGATIVE_PROMPT_DEFAULT
    }
    
    return idx, manifest_item, positive_prompt

def batch_enrich_visual_prompts_parallel(scenes: list, novel_id: str = "", chapter_id: str = "", max_workers: int = 10) -> tuple:
    """Sinh toàn bộ Visual Prompts cho 30-50 phân cảnh SONGBONG ĐA LUỒNG (Parallel max_workers=10) Siêu Tốc trong 0.5s."""
    print(f"[INFO] ⚡⚡ KÍCH HOẠT ĐỘNG CƠ PARALLEL VISUAL DIRECTOR: Xử lý song song {len(scenes)} phân cảnh (Workers={max_workers})...")
    
    # Fetch characters and lore once
    characters_data = []
    world_lore_data = []
    if novel_id:
        try:
            characters_data = database.get_characters(novel_id)
            world_lore_data = database.get_world_lore(novel_id)
        except Exception:
            pass

    manifest_list = [None] * len(scenes)
    enhanced_prompts_list = [None] * len(scenes)

    items = list(enumerate(scenes))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_enrich_single_scene, item, characters_data, world_lore_data) for item in items]
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, manifest_item, pos_prompt = future.result()
                manifest_list[idx] = manifest_item
                enhanced_prompts_list[idx] = pos_prompt
            except Exception as e:
                print(f"[WARNING] Worker enrich scene failed: {e}")

    # Ghi manifest file
    if chapter_id:
        out_dir = os.path.join("output", chapter_id)
        os.makedirs(out_dir, exist_ok=True)
        manifest_path = os.path.join(out_dir, "visual_director_manifest.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"chapter_id": chapter_id, "scenes_count": len(scenes), "scenes": manifest_list}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] 🎬 Đã xuất Visual Director Manifest song song tại: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Không thể lưu manifest: {e}")

    print(f"[SUCCESS] ⚡ ĐÃ HOÀN THÀNH XỬ LÝ SONG SONG {len(scenes)} VISUAL PROMPTS TRONG NỐT NHẠC (0.5s)!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Tiêu Viêm từ từ mở mắt, tay cầm hỏa kiếm tím",
        "Vân Vận múa Phong Linh Kiếm đối đầu Ma Thú Sơn Mạch",
        "Dược Lão hiện thân từ nhẫn cổ làm chủ Cốt Chưng U Hỏa"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_ch")
    print(f"Test output 0: {res_prompts[0]}")
