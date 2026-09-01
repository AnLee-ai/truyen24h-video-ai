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

def _enrich_single_scene(item: tuple, characters_data: list, world_lore_data: list, novel_genre_info: str) -> tuple:
    """Xử lý 1 phân cảnh bằng cách truyền 12 Luồng Thông Tin vào LLM để tạo Masterpiece Prompt."""
    idx, scene_text, prev_scene, next_scene = item
    
    # 1. Kí tự cache để tăng tốc
    cache_key = f"{scene_text}|{prev_scene}"
    if cache_key in _PROMPT_CACHE:
        print(f"[INFO] Scene {idx+1} hit Smart Cache. Thời gian xử lý: 0ms")
        return idx, _PROMPT_CACHE[cache_key]["manifest"], _PROMPT_CACHE[cache_key]["positive_prompt"], _PROMPT_CACHE[cache_key]["negative_prompt"]

    # 2 & 3: Trích xuất Character & Environment Locks
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

    # 4 & 5: Camera & Lighting
    camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
    lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]

    char_lock_str = " | ".join(char_lock_prompts)
    env_lock_str = " | ".join(env_lock_prompts)

    # GỌI LLM (12-POINT CONTEXT MASTER DIRECTOR)
    prompt_engineer_instruction = f"""
You are an elite Hollywood Visual Director and AI Image Generation Prompt Engineer (expert in Midjourney v6, SDXL, and FLUX).
Your task is to analyze a Vietnamese scene along with 11 other data streams, and output a highly optimized English image generation prompt.

Follow these strict rules:
1. OUTPUT PURE JSON ONLY. Do not use markdown ```json blocks. Just output raw JSON.
2. Structure the JSON EXACTLY with these keys: "reasoning", "time_of_day", "weather", "emotion", "color_palette", "positive_prompt", "negative_prompt".
3. REASONING: Explain in 1 sentence your choices for weather, emotion, and colors based on the scene and genre context.
4. CHARACTER ACCURACY: Replace character names with their exact physical descriptions from CHARACTER LOCKS.
5. ENVIRONMENT ACCURACY: Embed the ENVIRONMENT LOCKS visually.
6. STYLE: The style must be "masterpiece, best quality, 2D manhwa webtoon style, cel shaded, epic composition, ultra-detailed".
7. NEGATIVE PROMPT: Generate a custom negative prompt tailored to the scene (e.g. if historical, ban modern items). Always append: "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands".

--- 12-POINT INPUT CONTEXT ---
1. Novel Genre/Lore: {novel_genre_info}
2. Previous Scene: {prev_scene}
3. CURRENT SCENE TO DRAW: {scene_text}
4. Next Scene: {next_scene}
5. Character Locks: {char_lock_str}
6. Environment Locks: {env_lock_str}
7. Suggested Camera Angle: {camera}
8. Suggested Lighting: {lighting}
9-12. (You must deduce Time of Day, Weather, Emotion, Color Palette and output them in the JSON).
------------------------------

OUTPUT FORMAT:
{{
  "reasoning": "...",
  "time_of_day": "...",
  "weather": "...",
  "emotion": "...",
  "color_palette": "...",
  "positive_prompt": "...",
  "negative_prompt": "..."
}}
"""

    print(f"[INFO] Gửi Scene {idx+1} cho 12-Point Visual Director LLM...")
    enhanced_english_prompt = ""
    dynamic_negative_prompt = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands"
    ai_metadata = {}

    try:
        raw_llm_response = call_gemini(prompt_engineer_instruction, retries=2)
        if raw_llm_response:
            cleaned_llm = raw_llm_response.replace("```json", "").replace("```", "").strip()
            start_idx = cleaned_llm.find("{")
            end_idx = cleaned_llm.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned_llm = cleaned_llm[start_idx:end_idx+1]
                data = json.loads(cleaned_llm)
                
                # Combine deduced data into the prompt for maximum Midjourney effect
                time_wth = f"{data.get('time_of_day', '')}, {data.get('weather', '')}"
                colors_mood = f"{data.get('color_palette', '')} color palette, {data.get('emotion', '')} mood"
                
                enhanced_english_prompt = f"{data.get('positive_prompt', '')}, {time_wth}, {colors_mood}"
                dynamic_negative_prompt = data.get("negative_prompt", dynamic_negative_prompt)
                ai_metadata = {
                    "reasoning": data.get("reasoning", ""),
                    "time_of_day": data.get("time_of_day", ""),
                    "weather": data.get("weather", ""),
                    "emotion": data.get("emotion", ""),
                    "color_palette": data.get("color_palette", "")
                }
                print(f"[SUCCESS] 12-Point LLM JSON Parsed cho Scene {idx+1} | Mood: {ai_metadata['emotion']}")
    except Exception as e:
        print(f"[WARNING] LLM 12-Point Director failed parsing JSON for scene {idx+1}: {e}")

    # Fallback Cứng (Hard Translation)
    if not enhanced_english_prompt:
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
        "ai_analysis_metadata": ai_metadata,
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
    """Sinh toàn bộ Visual Prompts bằng LLM với 12-Point Context Engine (V3)."""
    print(f"[INFO] KÍCH HOẠT VISUAL DIRECTOR V3 (12-Point Context Engine): Xử lý song song {len(scenes)} phân cảnh...")
    
    characters_data = []
    world_lore_data = []
    novel_genre_info = "Epic Fantasy / Action"
    
    if novel_id:
        try:
            characters_data = database.get_characters(novel_id)
            world_lore_data = database.get_world_lore(novel_id)
            # Add fallback if method doesn't exist
            if hasattr(database, "get_novel_genre_info"):
                novel_genre_info = database.get_novel_genre_info(novel_id)
        except Exception as e:
            print(f"[WARNING] Failed to fetch 12-point contexts: {e}")

    manifest_list = [None] * len(scenes)
    enhanced_prompts_list = [None] * len(scenes)
    
    # Chuẩn bị items với 12 ngữ cảnh
    items = []
    for i in range(len(scenes)):
        prev_scene = scenes[i-1] if i > 0 else "None (Start of the chapter)"
        next_scene = scenes[i+1] if i < len(scenes) - 1 else "None (End of the chapter)"
        items.append((i, scenes[i], prev_scene, next_scene))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_enrich_single_scene, item, characters_data, world_lore_data, novel_genre_info): item for item in items}
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
                json.dump({"chapter_id": chapter_id, "novel_id": novel_id, "scenes_count": len(scenes), "v3_12_point_engine": True, "scenes": safe_manifest_data}, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Đã xuất Visual Director Manifest V3 tại: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Không thể lưu manifest: {e}")

    print(f"[SUCCESS] ĐÃ HOÀN THÀNH VISUAL DIRECTOR V3 (12 DATA POINTS) CHO {len(scenes)} CẢNH!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Một thanh niên bí ẩn đứng giữa thành phố hiện đại, cầm thanh gươm laser",
        "Cô gái trẻ bay lượn trên bầu trời hoàng hôn của vương quốc phép thuật",
        "Đại ma vương xuất hiện từ cánh cổng không gian"
    ]
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, chapter_id="test_lock_ch", max_workers=1)
    print(f"Test output 0 (V3 Prompt): {res_prompts[0]}")
