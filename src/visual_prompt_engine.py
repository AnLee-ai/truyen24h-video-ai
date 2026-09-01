import os
import re
import json
import concurrent.futures
import time
from src import database
from src.writer import call_gemini

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

NEGATIVE_PROMPT_DEFAULT = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands"

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list) -> tuple:
    """Xử lý 1 phân cảnh bằng cách truyền Dữ liệu Khóa vào LLM để tạo Prompt Tiếng Anh tối ưu."""
    idx, scene_text = item
    
    # 1. Trích xuất Ngoại hình & Đặc điểm nhân vật (Character Visual Lock)
    detected_chars = []
    char_lock_prompts = []
    for c in characters_data:
        c_name = c.get("name", "")
        if c_name and re.search(rf'\b{re.escape(c_name.lower())}\b', scene_text.lower()):
            detected_chars.append(c_name)
            if c_name in MASTER_CHARACTER_LOCKS:
                char_lock_prompts.append(f"{c_name}: {MASTER_CHARACTER_LOCKS[c_name]}")
            else:
                desc = c.get("description", "")
                power = c.get("power_tier", "")
                char_lock_prompts.append(f"{c_name}: {desc[:100]}, {power}")
                
    if not char_lock_prompts:
        char_lock_prompts.append("Cinematic focal character")

    # 2. Trích xuất Bối cảnh & Môi trường (Environment Visual Lock)
    detected_lore = []
    env_lock_prompts = []
    for lore_item in world_lore_data:
        kw = lore_item.get("keyword", "")
        if kw and re.search(rf'\b{re.escape(kw)}\b', scene_text):
            detected_lore.append(kw)
            if kw in MASTER_ENVIRONMENT_LOCKS:
                env_lock_prompts.append(f"{kw}: {MASTER_ENVIRONMENT_LOCKS[kw]}")
            else:
                desc = lore_item.get("description", "")
                env_lock_prompts.append(f"{kw}: {desc[:100]}")

    for env_kw, env_anchor in MASTER_ENVIRONMENT_LOCKS.items():
        if re.search(rf'\b{re.escape(env_kw)}\b', scene_text) and env_anchor not in env_lock_prompts:
            env_lock_prompts.append(f"{env_kw}: {env_anchor}")

    if not env_lock_prompts:
        env_lock_prompts.append("Cinematic atmospheric background")

    # 3. Phối đạo diễn Camera & Ánh sáng
    camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
    lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]

    char_lock_str = " | ".join(char_lock_prompts)
    env_lock_str = " | ".join(env_lock_prompts)

    # 4. GỌI LLM (Visual Prompt Engineer Agent)
    prompt_engineer_instruction = f"""
You are an elite AI Image Generation Prompt Engineer (expert in Midjourney v6, SDXL, and FLUX).
Your task is to take a scene written in Vietnamese, along with the character and environment details, and output a SINGLE, highly optimized English image generation prompt.

Follow these strict rules:
1. NO conversational text. Output ONLY the English prompt. DO NOT use markdown code blocks like ```. Just output the raw prompt.
2. Structure the prompt clearly: [Subject & Action], [Setting & Environment], [Camera & Lighting], [Style & Rendering].
3. CHARACTER ACCURACY IS PARAMOUNT: When a character is mentioned, DO NOT just use their name. You MUST replace or combine their name with their exact physical description provided in the CHARACTER LOCKS. For example, instead of "Xiao Yan is fighting", write "Xiao Yan, a young man with messy black hair, wearing a torn black robe, wielding a giant dark fire sword, is fighting".
4. ENVIRONMENT ACCURACY: Do the same for environments based on the ENVIRONMENT LOCKS.
5. STYLE: Ensure the style is exactly "masterpiece, 2D manhwa webtoon style, cel shaded, vibrant colors, epic composition, ultra-detailed".

INPUT:
- Scene (Vietnamese): {scene_text}
- Character Locks: {char_lock_str}
- Environment Locks: {env_lock_str}
- Camera Angle: {camera}
- Lighting: {lighting}

OUTPUT PURE ENGLISH PROMPT:
"""

    print(f"[INFO] Gửi Scene {idx+1} cho LLM Visual Prompt Engineer...")
    # Thử gọi LLM, nếu lỗi sẽ dùng cách ghép chuỗi truyền thống (Fallback)
    enhanced_english_prompt = ""
    try:
        raw_llm_response = call_gemini(prompt_engineer_instruction, retries=2)
        if raw_llm_response and len(raw_llm_response.split()) > 10:
            # Loại bỏ markdown nếu LLM cố tình trả về
            cleaned_llm = raw_llm_response.replace("```", "").replace("markdown", "").replace("TEXT", "").strip()
            enhanced_english_prompt = cleaned_llm
            print(f"[SUCCESS] Đã dịch & tối ưu hóa Prompt Tiếng Anh cho Scene {idx+1}")
    except Exception as e:
        print(f"[WARNING] LLM Visual Prompt Engineer failed for scene {idx+1}: {e}")

    # Fallback nếu LLM thất bại
    if not enhanced_english_prompt:
        enhanced_english_prompt = (
            f"masterpiece, best quality, 2D manhwa webtoon style, {scene_text}, "
            f"CHARACTER_LOCK: [{char_lock_str}], ENVIRONMENT_LOCK: [{env_lock_str}], "
            f"camera: [{camera}], lighting: [{lighting}], cel shaded, sharp line art, ultra-detailed, razor sharp focus, high contrast, 8k resolution"
        )

    manifest_item = {
        "scene_index": idx + 1,
        "raw_text_vietnamese": scene_text,
        "detected_characters": detected_chars,
        "detected_lore": detected_lore,
        "character_lock": char_lock_str,
        "environment_lock": env_lock_str,
        "camera_angle": camera,
        "lighting": lighting,
        "enhanced_english_prompt": enhanced_english_prompt,
        "negative_prompt": NEGATIVE_PROMPT_DEFAULT
    }
    
    return idx, manifest_item, enhanced_english_prompt

def batch_enrich_visual_prompts_parallel(scenes: list, novel_id: str = "", chapter_id: str = "", max_workers: int = 3) -> tuple:
    """Sinh toàn bộ Visual Prompts bằng LLM. Dùng max_workers=3 để tránh bị Rate Limit Gemini."""
    print(f"[INFO] KÍCH HOẠT ĐỘNG CƠ VISUAL DIRECTOR LLM: Dịch và Tối ưu hóa song song {len(scenes)} phân cảnh (Workers={max_workers})...")
    
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
    # Sử dụng luồng nhưng giới hạn tốc độ một chút để LLM không bị ngợp
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_enrich_single_scene, item, characters_data, world_lore_data): item for item in items}
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, manifest_item, pos_prompt = future.result()
                manifest_list[idx] = manifest_item
                enhanced_prompts_list[idx] = pos_prompt
            except Exception as e:
                item = futures[future]
                idx = item[0]
                print(f"[WARNING] Worker enrich scene {idx+1} failed: {e}")

    for i in range(len(scenes)):
        if not enhanced_prompts_list[i]:
            enhanced_prompts_list[i] = f"masterpiece, 2D manhwa webtoon style, {scenes[i]}"
        if not manifest_list[i]:
            manifest_list[i] = {"scene_index": i+1, "raw_text_vietnamese": scenes[i]}

    if chapter_id:
        out_dir = os.path.join("output", chapter_id)
        os.makedirs(out_dir, exist_ok=True)
        manifest_path = os.path.join(out_dir, "visual_director_manifest.json")
        try:
            raw_json = json.dumps(manifest_list, ensure_ascii=False)
            sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_json)
            safe_manifest_data = json.loads(sanitized)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"chapter_id": chapter_id, "scenes_count": len(scenes), "llm_enhanced": True, "scenes": safe_manifest_data}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Đã xuất Visual Director Manifest với Prompt Tiếng Anh tại: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Không thể lưu manifest: {e}")

    print(f"[SUCCESS] ĐÃ HOÀN THÀNH DỊCH VÀ TỐI ƯU HÓA LLM CHO {len(scenes)} VISUAL PROMPTS!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Một thanh niên bí ẩn đứng giữa thành phố hiện đại, cầm thanh gươm laser",
        "Cô gái trẻ bay lượn trên bầu trời hoàng hôn của vương quốc phép thuật",
        "Đại ma vương xuất hiện từ cánh cổng không gian"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_lock_ch", max_workers=1)
    print(f"Test output 0 (English LLM Prompt): {res_prompts[0]}")
