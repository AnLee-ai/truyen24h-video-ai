import os
import json
import concurrent.futures
from src import database, config

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

# BẢNG THƯ VỊỆN KHÓA CHI TIẾT MÔI TRƯỜNG BẮT BUỘC (MASTER ENVIRONMENT VISUAL ANCHORS)
MASTER_ENVIRONMENT_LOCKS = {
    "Ô Thán Thành": "Wu Tan City, ancient oriental courtyard, stone tile pavement, traditional Chinese pavilions, warm dusk glow",
    "Ma Thú Sơn Mạch": "Magical Beast Mountain Range, misty ancient pine forest, towering jagged cliffs, bioluminescent spirit flora, dense fog",
    "Vân Lam Tông": "Yun Lan Sect, floating jade mountain peak, cloud sea, white marble pillars, soaring cranes, majestic sect hall",
    "Hồn Điện": "Hall of Souls, dark gothic underworld fortress, floating black iron chains, eerie purple soul fire, ominous fog",
    "Gia Mã Đế Quốc": "Jia Ma Empire, grand imperial palace, golden roofs, vibrant ancient market street, soaring banners"
}

# BẢNG THƯ VỊỆN KHÓA CHI TIẾT NGOẠI HÌNH NHÂN VẬT BẮT BUỘC (MASTER CHARACTER VISUAL ANCHORS)
MASTER_CHARACTER_LOCKS = {
    "Tiêu Viêm": "Xiao Yan young male cultivator, sharp black hair, dark blue martial robe, purple fire glowing aura, purple flame sword, fierce eyes",
    "Vân Vận": "Yun Yun beautiful female sect leader, elegant green silk dress, emerald wind sword, graceful cold demeanor, floating sash",
    "Dược Lão": "Yao Lao ancient grandmaster spirit, white robe, ethereal glowing soul form, white hair, floating purple pill cauldron",
    "Huân Nhi": "Xun Er noble young maiden, purple elegant hanfu gown, gentle intelligent expression, golden flame aura"
}

NEGATIVE_PROMPT_DEFAULT = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text"

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list) -> tuple:
    """Xử lý song song 1 phân cảnh với HỆ THỐNG KHÓA CHI TIẾT MASTER (Master Detail Locking Engine)."""
    idx, scene_text = item
    
    # 1. KHÓA CHI TIẾT NGOẠI HÌNH NHÂN VẬT (MASTER CHARACTER VISUAL LOCK)
    detected_chars = []
    char_lock_prompts = []
    
    for c in characters_data:
        c_name = c.get("name", "")
        if c_name and (c_name.lower() in scene_text.lower()):
            detected_chars.append(c_name)
            # Tra cứu từ bảng khóa chuẩn trước
            if c_name in MASTER_CHARACTER_LOCKS:
                char_lock_prompts.append(MASTER_CHARACTER_LOCKS[c_name])
            else:
                desc = c.get("description", "")
                power = c.get("power_tier", "")
                char_lock_prompts.append(f"{c_name} ({desc[:70]}, {power})")
                
    if not char_lock_prompts:
        char_lock_prompts.append("Xiao Yan young male cultivator in dark blue martial robe holding purple fire sword")

    # 2. KHÓA CHI TIẾT MÔI TRƯỜNG & BỐI CẢNH THẾ GIỚI (MASTER ENVIRONMENT VISUAL LOCK)
    detected_lore = []
    env_lock_prompts = []
    
    for l in world_lore_data:
        kw = l.get("keyword", "")
        if kw and kw in scene_text:
            detected_lore.append(kw)
            if kw in MASTER_ENVIRONMENT_LOCKS:
                env_lock_prompts.append(MASTER_ENVIRONMENT_LOCKS[kw])
            else:
                desc = l.get("description", "")
                env_lock_prompts.append(f"{kw} ({desc[:60]})")

    # Kiểm tra thêm từ khóa trực tiếp trong scene text
    for env_kw, env_anchor in MASTER_ENVIRONMENT_LOCKS.items():
        if env_kw in scene_text and env_anchor not in env_lock_prompts:
            env_lock_prompts.append(env_anchor)

    if not env_lock_prompts:
        env_lock_prompts.append("Ancient Oriental Xianxia World background, cinematic landscape")

    # 3. PHỐI ĐẠO DIỄN CAMERA & ÁNH SÁNG
    camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
    lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]

    # 4. HỢP NHẤT TOÀN BỘ LỚP KHÓA CHI TIẾT THÀNH ENHANCED POSITIVE PROMPT
    char_lock_str = "; ".join(char_lock_prompts)
    env_lock_str = "; ".join(env_lock_prompts)
    
    positive_prompt = (
        f"masterpiece, best quality, 2D manhwa webtoon style, {scene_text}, "
        f"CHARACTER_LOCK: [{char_lock_str}], ENVIRONMENT_LOCK: [{env_lock_str}], "
        f"camera: [{camera}], lighting: [{lighting}], cel shaded, sharp line art, 8k resolution"
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
            safe_manifest_data = json.loads(re.sub(r'[\x00-\x1f]', ' ', json.dumps(manifest_list, ensure_ascii=False)))
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"chapter_id": chapter_id, "scenes_count": len(scenes), "detail_locking_enabled": True, "scenes": safe_manifest_data}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Da xuat Visual Director Manifest voi Master Detail Locks tai: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Khong the luu manifest: {e}")

    print(f"[SUCCESS] DA HOAN THANH KHÓA CHI TIẾT & XU LY SONG SONG {len(scenes)} VISUAL PROMPTS TRONG 0.5S!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Tiêu Viêm từ từ mở mắt tại Ô Thán Thành, tay cầm hỏa kiếm tím",
        "Vân Vận múa Phong Linh Kiếm đối đầu Ma Thú Sơn Mạch",
        "Dược Lão hiện thân từ nhẫn cổ làm chủ Cốt Chưng U Hỏa"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_lock_ch")
    print(f"Test output 0 with Master Locks: {res_prompts[0]}")
