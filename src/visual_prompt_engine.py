import os
import re
import json
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

def static_weave(translated_text: str, characters_data: list, world_lore_data: list) -> tuple:
    """Quét văn bản và chèn cứng thông tin nhân vật/bối cảnh bằng Python Regex."""
    char_prompts = []
    env_prompts = []
    weaved_text = translated_text
    
    # Weave characters
    for c in characters_data:
        # Note: API might translate names, so we check english aliases if they exist, 
        # but normally translated text retains pinyin names
        name = c.get("name", "")
        if not name: continue
        
        # Biểu thức chính quy tìm tên (không phân biệt hoa thường)
        pattern = re.compile(rf'\b{re.escape(name)}\b', re.IGNORECASE)
        if pattern.search(weaved_text):
            desc = c.get("description", "")[:150]
            power = c.get("power_tier", "")
            locked_detail = f"({desc}, {power})"
            # Gắn vào ngay sau tên nhân vật
            weaved_text = pattern.sub(f"{name} {locked_detail}", weaved_text)
            char_prompts.append(name)
            
    # Weave environment
    for lore in world_lore_data:
        kw = lore.get("keyword", "")
        if not kw: continue
        
        pattern = re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
        if pattern.search(weaved_text):
            desc = lore.get("description", "")[:150]
            locked_detail = f"({desc})"
            weaved_text = pattern.sub(f"{kw} {locked_detail}", weaved_text)
            env_prompts.append(kw)
            
    return weaved_text, char_prompts, env_prompts

def batch_translate_scenes(scenes: list) -> list:
    """Dịch mẻ (Batch) 1 lần duy nhất cho toàn bộ danh sách cảnh."""
    prompt = f"""
You are an expert translator. Translate the following JSON array of Vietnamese sentences into a JSON array of highly descriptive English sentences suitable for Midjourney prompts.
Return ONLY a valid JSON array of strings, exactly in the same order. Do not wrap in ```json or markdown.

INPUT:
{json.dumps(scenes, ensure_ascii=False)}
"""
    print(f"[INFO] Gửi lô {len(scenes)} phân cảnh cho AI dịch trong 1 lần duy nhất...")
    raw_response = call_gemini(prompt, json_mode=True, retries=2)
    
    translated_array = []
    if raw_response:
        try:
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start_idx = cleaned.find("[")
            end_idx = cleaned.rfind("]")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx+1]
                translated_array = json.loads(cleaned)
        except Exception as e:
            print(f"[WARNING] Lỗi phân tích JSON mảng dịch: {e}")
            
    if not translated_array or len(translated_array) != len(scenes):
        print("[WARNING] AI Batch Translation thất bại hoặc thiếu cảnh. Kích hoạt Fallback Deep-Translator...")
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='vi', target='en')
            translated_array = []
            for s in scenes:
                try:
                    translated_array.append(translator.translate(s))
                except Exception as e:
                    print(f"[WARNING] Deep-translator lỗi ở cảnh '{s}': {e}")
                    translated_array.append(s) # Fallback to original
        except ImportError:
            print("[WARNING] Không tìm thấy deep_translator. Giữ nguyên tiếng Việt.")
            translated_array = scenes.copy()
            
    return translated_array

def batch_enrich_visual_prompts_parallel(scenes: list, novel_id: str = "", chapter_id: str = "", max_workers: int = 1) -> tuple:
    """Sinh Visual Prompts với kiến trúc V4 (Crash-Proof Batch Engine) siêu tốc."""
    print(f"[INFO] KÍCH HOẠT VISUAL DIRECTOR V4 (Crash-Proof Engine): Dịch mẻ {len(scenes)} cảnh...")
    
    characters_data = []
    world_lore_data = []
    
    if novel_id:
        try:
            characters_data = database.get_characters(novel_id)
            world_lore_data = database.get_world_lore(novel_id)
        except Exception as e:
            print(f"[WARNING] Failed to fetch lore for weaving: {e}")

    # Bước 1: Gọi AI dịch 1 lần duy nhất
    translated_scenes = batch_translate_scenes(scenes)
    
    manifest_list = []
    enhanced_prompts_list = []
    dynamic_negative_prompt = "blurry, extra limbs, bad anatomy, deformed, distorted, 3d photorealistic, out of style, lowres, watermark, text, signature, bad proportions, bad hands"

    # Bước 2: Static Weaving bằng Python
    for idx, (vi_scene, en_scene) in enumerate(zip(scenes, translated_scenes)):
        # Gắn ngoại hình
        weaved_text, detected_chars, detected_lore = static_weave(en_scene, characters_data, world_lore_data)
        
        # Gắn Camera và Lighting luân phiên
        camera = CAMERA_ANGLES[idx % len(CAMERA_ANGLES)]
        lighting = LIGHTING_STYLES[idx % len(LIGHTING_STYLES)]
        
        final_prompt = f"masterpiece, best quality, 2D manhwa webtoon style, {weaved_text}, {camera}, {lighting}"
        
        manifest_item = {
            "scene_index": idx + 1,
            "raw_text_vietnamese": vi_scene,
            "translated_english": en_scene,
            "detected_characters": detected_chars,
            "detected_lore": detected_lore,
            "camera_angle": camera,
            "lighting": lighting,
            "enhanced_english_prompt": final_prompt,
            "negative_prompt": dynamic_negative_prompt
        }
        
        manifest_list.append(manifest_item)
        enhanced_prompts_list.append(final_prompt)

    # Bước 3: Lưu Output
    if chapter_id:
        out_dir = os.path.join("output", chapter_id)
        os.makedirs(out_dir, exist_ok=True)
        manifest_path = os.path.join(out_dir, "visual_director_manifest.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({
                    "chapter_id": chapter_id, 
                    "novel_id": novel_id, 
                    "scenes_count": len(scenes), 
                    "v4_crash_proof_engine": True, 
                    "scenes": manifest_list
                }, f, ensure_ascii=False, indent=2)
            print(f"[SUCCESS] Đã xuất Visual Director Manifest V4 tại: {manifest_path}")
        except Exception as e:
            print(f"[WARNING] Không thể lưu manifest: {e}")

    print(f"[SUCCESS] ĐÃ HOÀN THÀNH VISUAL DIRECTOR V4 (CRASH-PROOF) CHO {len(scenes)} CẢNH!")
    return manifest_list, enhanced_prompts_list

if __name__ == "__main__":
    test_scenes = [
        "Một thanh niên bí ẩn tên Xiao Yan đứng giữa thành phố hiện đại, cầm thanh gươm laser",
        "Cô gái trẻ bay lượn trên bầu trời hoàng hôn của học viện phép thuật",
        "Đại ma vương xuất hiện từ cánh cổng không gian"
    ]
    # Fake char for test
    fake_chars = [{"name": "Xiao Yan", "description": "handsome young boy with black robes", "power_tier": "Level 1"}]
    
    # We test V4 by passing mocked data since novel_id="" will skip DB
    database.get_characters = lambda x: fake_chars
    
    res_manifest, res_prompts = batch_enrich_visual_prompts_parallel(test_scenes, novel_id="fake", chapter_id="test_lock_ch_v4", max_workers=1)
    print(f"Test output 0 (V4 Prompt): {res_prompts[0]}")
