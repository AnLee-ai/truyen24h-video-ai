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
            print("[INFO] 🎵 Chưa có file BGM trong bgm/ folder. Tự động sinh nhạc nền Ambient Tiên Hiệp du dương (-24dB)...")
            from pydub.generators import Sine
            # Sinh sóng Sine du dương 440Hz dịu nhẹ làm nhạc nền mượt mà
            ambient_sound = Sine(440).to_audio_segment(duration=len(voice), volume=-28)
            ambient_sound = ambient_sound.fade_in(2000).fade_out(3000)
            final_mix = voice.overlay(ambient_sound)
            final_mix.export(output_path, format="mp3", bitrate="96k")
            print(f"[SUCCESS] Exported voice + ambient BGM audio to: {output_path}")
            return output_path
            
        # 3. Select a random BGM track
        selected_bgm_name = random.choice(bgm_files)
        bgm_path = os.path.join(config.BGM_DIR, selected_bgm_name)
        print(f"[INFO] Selected background music track: {selected_bgm_name}")
        
        bgm = AudioSegment.from_file(bgm_path)
        
        # 4. Process BGM: loop to match voice duration, lower volume, fade out
        # We target BGM volume to be around -20dB below voice DBFS level
        voice_db = voice.dbfs
        bgm_target_db = voice_db - 20
        bgm = bgm - (bgm.dbfs - bgm_target_db)
        
        # Loop BGM if it is shorter than the voice audio
        if len(bgm) < len(voice):
            loops_needed = (len(voice) // len(bgm)) + 1
            bgm = bgm * loops_needed
            
        # Trim BGM to match voice duration and apply fade-out
        bgm = bgm[:len(voice)]
        bgm = bgm.fade_out(3000) # 3-second fade out
        
        # 5. Overlay BGM and Voice
        print("[INFO] Mixing voice and background music...")
        final_mix = voice.overlay(bgm)
        
        # 6. Export mixed audio as MP3
        print(f"[INFO] Exporting mixed audio: {output_path}...")
        final_mix.export(output_path, format="mp3", bitrate="96k")
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
