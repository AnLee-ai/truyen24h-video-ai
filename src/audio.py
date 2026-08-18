import os
import random
from pydub import AudioSegment
from pydub.effects import normalize
from src import config

def mix_bgm_with_voice(voice_path: str, chapter_id: str) -> str:
    """
    Mix normalized raw voice audio with a random background music (BGM) track.
    
    Args:
        voice_path (str): Local path to the raw voice MP3 file.
        chapter_id (str): ID of the chapter.
        
    Returns:
        str: Path to the final mixed MP3 file.
    """
    output_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}_final.mp3")
    
    if not os.path.exists(voice_path):
        print(f"[ERROR] Voice audio file not found: {voice_path}")
        return ""
        
    try:
        print("[INFO] Loading voice audio...")
        voice = AudioSegment.from_mp3(voice_path)
        
        # 1. Normalize voice volume to prevent distortion
        print("[INFO] Normalizing voice audio volume...")
        voice = normalize(voice)
        
        os.makedirs(config.BGM_DIR, exist_ok=True)
        bgm_files = [f for f in os.listdir(config.BGM_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
        
        if not bgm_files:
            print("[INFO] Chưa có file BGM trong bgm/ folder. Kích hoạt Suno/Udio Webhook API...")
            webhook_url = os.environ.get("COLAB_WEBHOOK_SUNO_UDIO")
            if webhook_url:
                try:
                    import requests
                    resp = requests.get(webhook_url, timeout=60)
                    if resp.status_code == 200:
                        bgm_path = os.path.join(config.BGM_DIR, "suno_generated_bgm.mp3")
                        with open(bgm_path, "wb") as f:
                            f.write(resp.content)
                        bgm_files = ["suno_generated_bgm.mp3"]
                        print("[SUCCESS] Đã tải nhạc nền từ Suno/Udio Colab Webhook!")
                except Exception as e:
                    print(f"[WARNING] Lỗi tải Suno/Udio Webhook: {e}")
            if not bgm_files:
                voice.export(output_path, format="mp3", bitrate="192k")
                return output_path
            
        # 3. Select a random BGM track
        selected_bgm_name = random.choice(bgm_files)
        bgm_path = os.path.join(config.BGM_DIR, selected_bgm_name)
        print(f"[INFO] Selected background music track: {selected_bgm_name}")
        
        bgm = AudioSegment.from_file(bgm_path)
        
        # 4. Process BGM: loop to match voice duration, lower volume, fade out
        # We target BGM volume to be around -20dB below voice DBFS level
        voice_db = voice.dbfs if not (voice.dbfs == float('-inf') or voice.dbfs == float('inf')) else -15.0
        bgm_target_db = voice_db - 20
        bgm = bgm - (bgm.dbfs - bgm_target_db)
        
        # Loop BGM if it is shorter than the voice audio
        if len(bgm) < len(voice):
            loops_needed = (len(voice) // max(1, len(bgm))) + 1
            bgm = bgm * loops_needed
            
        # Trim BGM to match voice duration and apply fade-out safely
        fade_ms = min(3000, max(100, len(voice)))
        bgm = bgm[:len(voice)]
        bgm = bgm.fade_out(fade_ms)
        
        # 5. Overlay BGM and Voice
        print("[INFO] Mixing voice and background music...")
        final_mix = voice.overlay(bgm)
        
        # 6. Export mixed audio as MP3 (192k HQ)
        print(f"[INFO] Exporting mixed audio (192k HQ): {output_path}...")
        final_mix.export(output_path, format="mp3", bitrate="192k")
        return output_path
        
    except Exception as e:
        print(f"[ERROR] Failed to mix BGM and voice: {e}")
        # Fallback: copy raw voice if mix fails
        try:
            print("[INFO] Falling back to exporting raw voice...")
            import shutil
            shutil.copy(voice_path, output_path)
            return output_path
        except Exception as fallback_err:
            print(f"[ERROR] Fallback failed: {fallback_err}")
            return voice_path
