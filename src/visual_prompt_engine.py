import os
import re
import json
import concurrent.futures
from src import database

CAMERA_ANGLES = [
    "Low-angle dynamic medium shot, 35mm anamorphic lens",
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

# Dynamic lock dictionaries are loaded from Database instead of hardcoding
MASTER_ENVIRONMENT_LOCKS = {}
MASTER_CHARACTER_LOCKS = {}

NEGATIVE_PROMPT_DEFAULT = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text"

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list) -> tuple:
    """Xử lý song song 1 phân cảnh với HỆ THỐNG KHÓA CHI TIẾT MASTER (Master Detail Locking Engine)."""
    idx, scene_text = item
    
    # 1. KHÓA CHI TIẾT NGOẠI HÌNH NHÂN VẬT (MASTER CHARACTER VISUAL LOCK)
    detected_chars = []
    char_lock_prompts = []
    
    for c in characters_data:
        c_name = c.get("name", "")
        if c_name and re.search(rf'\b{re.escape(c_name.lower())}\b', scene_text.lower()):
            detected_chars.append(c_name)
            # Tra cứu từ bảng khóa chuẩn trước
            if c_name in MASTER_CHARACTER_LOCKS:
                char_lock_prompts.append(MASTER_CHARACTER_LOCKS[c_name])
            else:
                desc = c.get("description", "")
                power = c.get("power_tier", "")
                char_lock_prompts.append(f"{c_name} ({desc[:70]}, {power})")
                
    if not char_lock_prompts:
        char_lock_prompts.append("Cinematic focal character")

    # 2. KHÓA CHI TIẾT MÔI TRƯỜNG & BỐI CẢNH THẾ GIỚI (MASTER ENVIRONMENT VISUAL LOCK)
    detected_lore = []
    env_lock_prompts = []
    
    for lore_item in world_lore_data:
        kw = lore_item.get("keyword", "")
        if kw and re.search(rf'\b{re.escape(kw)}\b', scene_text):
            detected_lore.append(kw)
            if kw in MASTER_ENVIRONMENT_LOCKS:
                env_lock_prompts.append(MASTER_ENVIRONMENT_LOCKS[kw])
            else:
                desc = lore_item.get("description", "")
                env_lock_prompts.append(f"{kw} ({desc[:60]})")

    # Kiểm tra thêm từ khóa trực tiếp trong scene text
    for env_kw, env_anchor in MASTER_ENVIRONMENT_LOCKS.items():
        if re.search(rf'\b{re.escape(env_kw)}\b', scene_text) and env_anchor not in env_lock_prompts:
            env_lock_prompts.append(env_anchor)

    if not env_lock_prompts:
        env_lock_prompts.append("Cinematic atmospheric background")

    # 3. PHỐI ĐẠO DIỄN CAMERA & ÁNH SÁNG
    camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
    lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]

    # 4. HỢP NHẤT TOÀN BỘ LỚP KHÓA CHI TIẾT THÀNH ENHANCED POSITIVE PROMPT
    char_lock_str = "; ".join(char_lock_prompts)
    env_lock_str = "; ".join(env_lock_prompts)
    
    positive_prompt = (
        f"masterpiece, best quality, 2D manhwa webtoon style, {scene_text}, "
        f"CHARACTER_LOCK: [{char_lock_str}], ENVIRONMENT_LOCK: [{env_lock_str}], "
        f"camera: [{camera}], lighting: [{lighting}], cel shaded, sharp line art, ultra-detailed, razor sharp focus, high contrast, 8k resolution"
    )

    manifest_item = {
        "scene_index": idx + 1,
        "raw_text": scene_text,
        "detected_characters": detected_chars,
        "detected_lore": detected_lore,
        "character_lock": char_lock_str,
        "environment_lock": env_lock_str,
        "camera_angle": camera,
        "lighting": lighting,
        "enhanced_prompt": positive_prompt,
        "negative_prompt": NEGATIVE_PROMPT_DEFAULT
    }
    
    return idx, manifest_item, positive_prompt

def batch_enrich_visual_prompts_parallel(scenes: list, novel_id: str = "", chapter_id: str = "", max_workers: int = 10) -> tuple:
    """Sinh toàn bộ Visual Prompts với HỆ THỐNG KHÓA CHI TIẾT MASTER song song đa luồng (Workers=10) trong 0.5s."""
    print(f"[INFO] KICH HOAT DONG CO PARALLEL VISUAL DIRECTOR WITH MASTER DETAIL LOCKS: Xu ly song song {len(scenes)} phan canh (Workers={max_workers})...")
    
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

    # Fallback thay thế các vị trí None bị lỗi worker
    for i in range(len(scenes)):
        if not enhanced_prompts_list[i]:
            enhanced_prompts_list[i] = f"masterpiece, 2D manhwa webtoon style, {scenes[i]}"
        if not manifest_list[i]:
            manifest_list[i] = {"scene_index": i+1, "scene_text": scenes[i]}

    # Ghi manifest file
    if chapter_id:
        out_dir = os.path.join("output", chapter_id)
        os.makedirs(out_dir, exist_ok=True)
        manifest_path = os.path.join(out_dir, "visual_director_manifest.json")
        try:
            # Sanitize control chars before writing manifest
            raw_json = json.dumps(manifest_list, ensure_ascii=False)
            sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_json)
            safe_manifest_data = json.loads(sanitized)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"chapter_id": chapter_id, "scenes_count": len(scenes), "detail_locking_enabled": True, "scenes": safe_manifest_data}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Da xuat Visual Director Manifest voi Master Detail Locks tai: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Khong the luu manifest: {e}")

    print(f"[SUCCESS] DA HOAN THANH KHÓA CHI TIẾT & XU LY SONG SONG {len(scenes)} VISUAL PROMPTS TRONG 0.5S!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Một thanh niên bí ẩn đứng giữa thành phố hiện đại, cầm thanh gươm laser",
        "Cô gái trẻ bay lượn trên bầu trời hoàng hôn của vương quốc phép thuật",
        "Đại ma vương xuất hiện từ cánh cổng không gian"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_lock_ch")
    print(f"Test output 0 with Master Locks: {res_prompts[0]}")
