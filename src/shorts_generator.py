import os
import shutil
import subprocess
from typing import Optional
from src.image_generator import generate_scene_image

def generate_shorts_video(audio_path: str, srt_path: str, chapter_id: str, title: str = "Highlight") -> Optional[str]:
    """Tự động cắt 30-60s cao trào và render Video Shorts (9:16) chuẩn TikTok/Shorts kèm ảnh nền AI (100% Free)."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] File audio không tồn tại: {audio_path}")
        return None
        
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg chưa được cài đặt!")
        return None
        
    out_dir = os.path.join("output", chapter_id)
    os.makedirs(out_dir, exist_ok=True)
    shorts_video_path = os.path.join(out_dir, "shorts_video.mp4")
    
    print(f"[INFO] Bắt đầu tạo Video Shorts (9:16) cho: {title}...")
    
    # 1. Sinh ảnh nền AI kích thước dọc 1080x1920
    shorts_bg = os.path.join(out_dir, "background_shorts.jpg")
    if not os.path.exists(shorts_bg):
        generate_scene_image(title, shorts_bg, width=1080, height=1920)
        
    # 2. Chuẩn hóa phụ đề: Chữ trắng (&H00FFFFFF&), Viền đen mỏng (Outline=1), Cỡ chữ vừa (FontSize=20), 1 hàng (WrapStyle=2)
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path and os.path.exists(srt_path) else ""
    subtitle_style = "FontSize=20,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,Outline=1,Shadow=0,Alignment=2,MarginV=180,WrapStyle=2"
    
    vf_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=brightness=-0.15:contrast=1.1[bg]"
    if srt_escaped:
        vf_filter += f";[bg]subtitles='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    # 3. Tính toán thời gian bắt đầu an toàn (tránh seek vượt quá độ dài audio gây treo FFmpeg)
    start_ss = "00:00:10"
    try:
        prob = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
        dur = float(prob.stdout.strip())
        if dur <= 30.0:
            start_ss = "00:00:00"
    except Exception:
        pass

    if os.path.exists(shorts_bg) and os.path.getsize(shorts_bg) > 1000:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", shorts_bg,
            "-i", audio_path,
            "-ss", start_ss, "-t", "00:00:45",
            "-filter_complex", vf_filter,
            "-map", "[out]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", shorts_video_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
            "-i", audio_path,
            "-ss", start_ss, "-t", "00:00:45",
            "-vf", f"subtitles='{srt_escaped}':force_style='{subtitle_style}'" if srt_escaped else "null",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", shorts_video_path
        ]
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0 and os.path.exists(shorts_video_path):
            print(f"[SUCCESS] Tạo thành công Video Shorts (9:16): {shorts_video_path}")
            return shorts_video_path
        else:
            print(f"[WARNING] FFmpeg Shorts render warning: {res.stderr[:200]}")
    except Exception as e:
        print(f"[ERROR] Exception running Shorts FFmpeg: {e}")
        
    return None

if __name__ == "__main__":
    print("Shorts Generator Module Ready.")
