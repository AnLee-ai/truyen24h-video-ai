import os
import random
from pydub import AudioSegment
from pydub.effects import normalize
from src import config

def mix_bgm_with_voice(voice_path: str, chapter_id: str) -> str:
    """Mix normalized raw voice audio with a random background music track using ffmpeg to save RAM."""
    import subprocess, random
    output_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}_final.mp3")
    if not os.path.exists(voice_path):
        print(f"[ERROR] Voice audio file not found: {voice_path}")
        return ""
    try:
        print("[INFO] Preparing to mix audio using FFmpeg (RAM Optimized)...")
        os.makedirs(config.BGM_DIR, exist_ok=True)
        bgm_files = [f for f in os.listdir(config.BGM_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
        if not bgm_files:
            print("[INFO] Chưa có file BGM trong bgm/ folder. Kích hoạt Suno/Udio Webhook API...")
            webhook_url = os.environ.get("COLAB_WEBHOOK_SUNO_UDIO")
            if webhook_url:
                try:
                    import requests
                    resp = requests.get(webhook_url, timeout=60, stream=True)
                    if resp.status_code == 200:
                        bgm_path = os.path.join(config.BGM_DIR, "suno_generated_bgm.mp3")
                        with open(bgm_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                if chunk: f.write(chunk)
                        bgm_files = ["suno_generated_bgm.mp3"]
                        print("[SUCCESS] Đã tải nhạc nền từ Suno/Udio Colab Webhook!")
                except Exception as e:
                    print(f"[WARNING] Lỗi tải Suno/Udio Webhook: {e}")
            if not bgm_files:
                print("[INFO] No BGM found, skipping BGM mix (fast copy)...")
                import shutil
                shutil.copy2(voice_path, output_path)
                return output_path
        
        selected_bgm_name = random.choice(bgm_files)
        bgm_path = os.path.join(config.BGM_DIR, selected_bgm_name)
        print(f"[INFO] Selected background music track: {selected_bgm_name}")
        print("[INFO] Mixing voice and background music...")
        
        filter_complex = (
            "[0:a]volume=1.2[v];"
            "[1:a]volume=0.15[b];"
            "[v][b]amix=inputs=2:duration=first:dropout_transition=3[outa]"
        )
        subprocess.run([
            "ffmpeg", "-y", "-threads", "1", "-i", voice_path, "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", filter_complex, "-map", "[outa]",
            "-c:a", "libmp3lame", "-b:a", "192k", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception as e:
        print(f"[ERROR] Failed to mix BGM and voice: {e}")
        import shutil
        shutil.copy2(voice_path, output_path)
        return output_path

