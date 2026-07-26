import os
import shutil
import subprocess
from typing import Optional

def generate_shorts_video(audio_path: str, srt_path: str, chapter_id: str, title: str = "Highlight") -> Optional[str]:
    """Tự động cắt 30-60s cao trào và render Video Shorts (9:16) chuẩn TikTok/Shorts (100% Free)."""
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
    
    # 1. Chuẩn hóa đường dẫn SRT cho FFmpeg Windows
    srt_escaped = ""
    if srt_path and os.path.exists(srt_path):
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        
    # 2. Xây dựng lệnh FFmpeg crop 1080x1920 (dọc 9:16) + hiệu ứng phụ đề chữ to ở giữa
    if srt_escaped:
        vf_filter = f"subtitles='{srt_escaped}':force_style='FontSize=32,PrimaryColour=&H00FFFF&,Alignment=2,MarginV=400'"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
            "-ss", "00:00:30", "-t", "00:00:45", "-i", audio_path, # Cắt 45s từ giây thứ 30
            "-vf", vf_filter,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", shorts_video_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
            "-ss", "00:00:30", "-t", "00:00:45", "-i", audio_path,
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
