import os
import json
import subprocess
import shutil
from src.image_generator import generate_scene_image

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

def create_video_ffmpeg_fallback(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel") -> str:
    """Tạo video YouTube (1920x1080) bằng FFmpeg với ảnh nền AI + phụ đề Tiếng Việt chuẩn (Chữ trắng, viền đen mỏng, 1 hàng)."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg không được cài đặt!")
        return ""
        
    out_dir = os.path.dirname(output_video_path)
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Sinh ảnh minh họa AI nền nếu chưa có
    bg_image = os.path.join(out_dir, "background.jpg")
    if not os.path.exists(bg_image):
        print(f"[INFO] Đang sinh ảnh nền AI minh họa cho video: {title}...")
        generate_scene_image(title, bg_image, width=1920, height=1080)
        
    # 2. Định dạng phụ đề chuẩn: Chữ Trắng (&H00FFFFFF&), Viền Đen Mỏng (Outline=1), Cỡ chữ vừa nhỏ (FontSize=16), 1 hàng (WrapStyle=2)
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path and os.path.exists(srt_path) else ""
    subtitle_style = "FontSize=16,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,Outline=1,Shadow=0,Alignment=2,MarginV=35,WrapStyle=2"
    
    # 3. Phối hợp filter: Ảnh nền Ken Burns zoom + lớp phủ làm tối 30% + Phụ đề trắng viền đen
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=-0.15:contrast=1.1[bg]"
    if srt_escaped:
        vf_filter += f";[bg]subtitles='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    if os.path.exists(bg_image) and os.path.getsize(bg_image) > 1000:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg_image,
            "-i", audio_path,
            "-filter_complex", vf_filter,
            "-map", "[out]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", output_video_path
        ]
    else:
        # Fallback nền tối nếu không tải được ảnh
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30",
            "-i", audio_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{subtitle_style}'" if srt_escaped else "null",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", output_video_path
        ]
        
    try:
        print(f"[INFO] FFmpeg rendering video with AI background...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode == 0 and os.path.exists(output_video_path):
            print(f"[SUCCESS] Render video thành công với ảnh nền AI: {output_video_path}")
            return output_video_path
        else:
            print(f"[ERROR] FFmpeg error: {res.stderr[:300]}")
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
    print("[INFO] Chuyển sang render video tự động bằng FFmpeg với ảnh AI minh họa...")
    out_video = os.path.join("output", chapter_id, "video.mp4")
    return create_video_ffmpeg_fallback(audio_path, srt_path, out_video, title)

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
