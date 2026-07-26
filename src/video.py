import os
import json
import subprocess
import shutil

def generate_script_json(audio_path: str, srt_path: str, title: str, chapter_id: str) -> str:
    """Tạo file script.json đúng cấu trúc cho AI-auto-generate-video."""
    work_dir = os.path.join("output", chapter_id)
    os.makedirs(work_dir, exist_ok=True)
    
    script_data = {
        "id": chapter_id,
        "title": title,
        "audio": os.path.abspath(audio_path),
        "srt": os.path.abspath(srt_path) if srt_path and os.path.exists(srt_path) else "",
        "scenes": [
            {
                "text": title,
                "audio": os.path.abspath(audio_path),
                "duration": 0
            }
        ]
    }
    
    script_path = os.path.join(work_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
        
    return script_path

def create_video_with_ai_tool(script_json_path: str, tool_dir: str = "AI-auto-generate-video") -> str:
    """Gọi pipeline AI-auto-generate-video (Node.js/HyperFrames) nếu có."""
    if not os.path.exists(tool_dir):
        return ""
        
    try:
        cmd = ["npm", "run", "pipeline", "--", os.path.abspath(script_json_path)]
        print(f"[INFO] Running AI-auto-generate-video: {' '.join(cmd)}")
        res = subprocess.run(cmd, cwd=tool_dir, capture_output=True, text=True, timeout=600)
        
        if res.returncode == 0:
            out_dir = os.path.dirname(script_json_path)
            video_path = os.path.join(out_dir, "video.mp4")
            if os.path.exists(video_path):
                return video_path
    except Exception as e:
        print(f"[WARNING] AI-auto-generate-video failed: {e}")
        
    return ""

def create_video_ffmpeg_fallback(audio_path: str, srt_path: str, output_video_path: str) -> str:
    """Tạo video YouTube (1920x1080) bằng FFmpeg với audio + phụ đề SRT nếu Node tool chưa sẵn sàng."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg không được cài đặt!")
        return ""
        
    # Tạo background tối + sóng nhạc / phụ đề
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path else ""
    vf_filter = "color=c=black:s=1920x1080:r=30[bg]"
    
    if srt_escaped and os.path.exists(srt_path):
        vf_filter = f"color=c=black:s=1920x1080:r=30[bg];[bg]subtitles='{srt_escaped}':force_style='FontSize=24,PrimaryColour=&H00FFFF&,Alignment=2'[out]"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30",
            "-i", audio_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='FontSize=24,PrimaryColour=&H00FFFF&,Alignment=2'",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "1920k", "-pix_fmt", "yuv420p",
            "-shortest", output_video_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30",
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "1920k", "-pix_fmt", "yuv420p",
            "-shortest", output_video_path
        ]
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode == 0 and os.path.exists(output_video_path):
            return output_video_path
        else:
            print(f"[ERROR] FFmpeg error: {res.stderr}")
    except Exception as e:
        print(f"[ERROR] Exception running FFmpeg: {e}")
        
    return ""

def render_novel_video(audio_path: str, srt_path: str, title: str, chapter_id: str) -> str:
    """Tự động render video từ audio & SRT."""
    script_json = generate_script_json(audio_path, srt_path, title, chapter_id)
    
    # 1. Thử render bằng AI-auto-generate-video
    video_path = create_video_with_ai_tool(script_json)
    if video_path and os.path.exists(video_path):
        print(f"[INFO] Video render thành công qua AI-auto-generate-video: {video_path}")
        return video_path
        
    # 2. Fallback sang FFmpeg nếu chưa setup Node tool
    print("[INFO] Chuyển sang render video tự động bằng FFmpeg fallback...")
    out_video = os.path.join("output", chapter_id, "video.mp4")
    return create_video_ffmpeg_fallback(audio_path, srt_path, out_video)

def process_existing_audio(audio_path: str, srt_path: str = "", title: str = "Audiobook Novel") -> str:
    """Hàm độc lập: Nhận trực tiếp file audio có sẵn từ workflow và xuất video MP4."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] File audio không tồn tại: {audio_path}")
        return ""
        
    import uuid
    chapter_id = str(uuid.uuid4())[:8]
    print(f"[INFO] Đang xử lý file audio có sẵn: {audio_path}")
    return render_novel_video(audio_path, srt_path, title, chapter_id)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        aud = sys.argv[1]
        srt = sys.argv[2] if len(sys.argv) > 2 else ""
        ttl = sys.argv[3] if len(sys.argv) > 3 else "Audiobook Novel"
        res = process_existing_audio(aud, srt, ttl)
        print(f"Result video: {res}")
