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

# Caching to prevent re-translating the exact same scene
_PROMPT_CACHE = {}

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list) -> tuple:
    """Xử lý 1 phân cảnh bằng cách truyền Dữ liệu Khóa và Ngữ cảnh trước/sau vào LLM."""
    idx, scene_text, prev_scene, next_scene = item
    
    # Kí tự cache để tăng tốc
    cache_key = f"{scene_text}|{prev_scene}"
    if cache_key in _PROMPT_CACHE:
        print(f"[INFO] Scene {idx+1} hit Smart Cache. Thời gian xử lý: 0ms")
        return idx, _PROMPT_CACHE[cache_key]["manifest"], _PROMPT_CACHE[cache_key]["positive_prompt"], _PROMPT_CACHE[cache_key]["negative_prompt"]

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
                char_lock_prompts.append(f"{c_name}: {desc[:150]}, {power}")
                
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
                env_lock_prompts.append(f"{kw}: {desc[:150]}")

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

    # 4. GỌI LLM (Visual Prompt Engineer Agent) VỚI ĐỊNH DẠNG JSON
    prompt_engineer_instruction = f"""
You are an elite AI Image Generation Prompt Engineer (expert in Midjourney v6, SDXL, and FLUX).
Your task is to take a scene written in Vietnamese, along with the character and environment details, and output a highly optimized English image generation prompt.

Follow these strict rules:
1. OUTPUT PURE JSON ONLY. Do not use markdown ```json blocks. Just output raw JSON.
2. Structure the JSON with two keys: "positive_prompt" and "negative_prompt".
3. CHARACTER ACCURACY IS PARAMOUNT: When a character is mentioned, DO NOT just use their name. You MUST replace or combine their name with their exact physical description provided in the CHARACTER LOCKS.
4. ENVIRONMENT ACCURACY: Do the same for environments based on the ENVIRONMENT LOCKS.
5. STYLE: Ensure the style is exactly "masterpiece, best quality, 2D manhwa webtoon style, cel shaded, vibrant colors, epic composition, ultra-detailed".
6. CONTINUITY: Use the Previous Scene context to maintain consistent lighting, clothing state, and camera angles if it makes sense.
7. NEGATIVE PROMPT: Generate a custom negative prompt tailored to the scene (e.g. if it's a historical scene, add "modern, cars, phones"). Always include the base negative prompt: "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands".

INPUT:
- Previous Scene (For Continuity): {prev_scene}
- CURRENT SCENE TO DRAW (Vietnamese): {scene_text}
- Next Scene (For Foreshadowing): {next_scene}
- Character Locks: {char_lock_str}
- Environment Locks: {env_lock_str}
- Suggested Camera Angle: {camera}
- Suggested Lighting: {lighting}

OUTPUT FORMAT:
{{
  "positive_prompt": "...",
  "negative_prompt": "..."
}}
"""

    print(f"[INFO] Gửi Scene {idx+1} cho LLM Visual Prompt Engineer...")
    enhanced_english_prompt = ""
    dynamic_negative_prompt = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands"
    
    try:
        raw_llm_response = call_gemini(prompt_engineer_instruction, retries=2)
        if raw_llm_response:
            cleaned_llm = raw_llm_response.replace("```json", "").replace("```", "").strip()
            # Find JSON object boundaries
            start_idx = cleaned_llm.find("{")
            end_idx = cleaned_llm.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned_llm = cleaned_llm[start_idx:end_idx+1]
                data = json.loads(cleaned_llm)
                enhanced_english_prompt = data.get("positive_prompt", "")
                dynamic_negative_prompt = data.get("negative_prompt", dynamic_negative_prompt)
                print(f"[SUCCESS] Đã dịch & phân tích JSON thành công cho Scene {idx+1}")
    except Exception as e:
        print(f"[WARNING] LLM Visual Prompt Engineer failed parsing JSON for scene {idx+1}: {e}")

    # Fallback
    if not enhanced_english_prompt:
        import urllib.parse
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='vi', target='en').translate(scene_text)
            enhanced_english_prompt = f"masterpiece, best quality, 2D manhwa webtoon style, {translated}, {char_lock_str}, {env_lock_str}, {camera}, {lighting}"
        except Exception as trans_e:
            print(f"[WARNING] Fallback translation failed: {trans_e}")
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
        "negative_prompt": dynamic_negative_prompt
    }
    
    # Save to Cache
    _PROMPT_CACHE[cache_key] = {
        "manifest": manifest_item,
        "positive_prompt": enhanced_english_prompt,
        "negative_prompt": dynamic_negative_prompt
    }
    
    return idx, manifest_item, enhanced_english_prompt, dynamic_negative_prompt

def batch_enrich_visual_prompts_parallel(scenes: list, novel_id: str = "", chapter_id: str = "", max_workers: int = 5) -> tuple:
    """Sinh toàn bộ Visual Prompts bằng LLM với Master Detail Locks và Continuity."""
    print(f"[INFO] KÍCH HOẠT VISUAL DIRECTOR V2 (Continuity + JSON Output): Xử lý song song {len(scenes)} phân cảnh...")
    
    characters_data = []
    world_lore_data = []
    if novel_id:
        try:
            characters_data = database.get_characters(novel_id)
            world_lore_data = database.get_world_lore(novel_id)
        except Exception as e:
            print(f"[WARNING] Failed to fetch character locks: {e}")

    manifest_list = [None] * len(scenes)
    enhanced_prompts_list = [None] * len(scenes)
    
    # Chuẩn bị items với ngữ cảnh (previous và next)
    items = []
    for i in range(len(scenes)):
        prev_scene = scenes[i-1] if i > 0 else "None (Start of the chapter)"
        next_scene = scenes[i+1] if i < len(scenes) - 1 else "None (End of the chapter)"
        items.append((i, scenes[i], prev_scene, next_scene))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_enrich_single_scene, item, characters_data, world_lore_data): item for item in items}
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, manifest_item, pos_prompt, neg_prompt = future.result()
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
                json.dump({"chapter_id": chapter_id, "novel_id": novel_id, "scenes_count": len(scenes), "llm_enhanced": True, "scenes": safe_manifest_data}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Đã xuất Visual Director Manifest V2 tại: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Không thể lưu manifest: {e}")

    print(f"[SUCCESS] ĐÃ HOÀN THÀNH VISUAL DIRECTOR V2 CHO {len(scenes)} CẢNH!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Một thanh niên bí ẩn đứng giữa thành phố hiện đại, cầm thanh gươm laser",
        "Cô gái trẻ bay lượn trên bầu trời hoàng hôn của vương quốc phép thuật",
        "Đại ma vương xuất hiện từ cánh cổng không gian"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_lock_ch", max_workers=1)
    print(f"Test output 0 (English LLM Prompt): {res_prompts[0]}")
