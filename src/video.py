import os
import json
import re
import subprocess
import shutil
from src.image_generator import generate_scene_image

def parse_srt_scenes(srt_path: str, interval_seconds: int = 7) -> list:
    """Đọc file SRT và phân chia thành các đoạn cảnh 5-10 giây kèm văn bản thoại."""
    if not os.path.exists(srt_path):
        return []
        
    scenes = []
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        blocks = re.split(r'\n\s*\n', content.strip())
        current_text = []
        
        for idx, block in enumerate(blocks):
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) >= 2:
                text_lines = " ".join(lines[2:]) if lines[0].isdigit() else " ".join(lines[1:])
                current_text.append(text_lines)
                
                # Cứ 3-4 câu thoại (khoảng 7 giây) gộp thành 1 phân cảnh
                if len(current_text) >= 3 or idx == len(blocks) - 1:
                    scenes.append(" ".join(current_text))
                    current_text = []
    except Exception as e:
        print(f"[WARNING] Lỗi đọc SRT phân cảnh: {e}")
        
    return scenes if scenes else ["Mở đầu chương tiểu thuyết"]

def get_audio_duration_seconds(audio_path: str) -> float:
    """Lấy chính xác độ dài thời gian của file audio MP3 tính bằng giây."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception as e:
        print(f"[WARNING] Lỗi đo độ dài audio bằng ffprobe: {e}")
    return 0.0

def create_multi_image_slideshow_video(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel", interval: int = 7) -> str:
    """Tự động sinh ảnh AI và ghép thành video kéo dài 100% khớp độ dài audio kèm hiệu ứng Pan & Zoom điện ảnh nhẹ nhàng."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg không được cài đặt!")
        return ""
        
    out_dir = os.path.dirname(output_video_path)
    img_dir = os.path.join(out_dir, "scenes")
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Đo chính xác độ dài audio thực tế tính bằng giây
    total_audio_duration = get_audio_duration_seconds(audio_path)
    print(f"[INFO] Thời lượng thực tế của file Audio: {total_audio_duration:.2f} giây ({total_audio_duration/60:.2f} phút).")
    
    # 2. Phân đoạn cảnh từ SRT
    scenes = parse_srt_scenes(srt_path, interval_seconds=interval)
    
    # Tính số lượng ảnh cần phủ kín toàn bộ thời lượng audio
    required_images_count = int(total_audio_duration / interval) + 2 if total_audio_duration > 0 else len(scenes)
    print(f"[INFO] Tổng số phân cảnh sinh ảnh AI (cần {required_images_count} ảnh để phủ kín {total_audio_duration:.1f}s): {len(scenes)}")
    
    # 3. Sinh ảnh AI ĐA LUỒNG cho các phân cảnh (tối đa 40 ảnh)
    from src.image_generator import batch_generate_scene_images
    chapter_id = os.path.basename(out_dir)
    image_files = batch_generate_scene_images(scenes[:40], chapter_id=chapter_id, max_workers=4)
            
    if not image_files:
        bg_image = os.path.join(out_dir, "background.jpg")
        generate_scene_image(title, bg_image, width=1920, height=1080)
        if os.path.exists(bg_image):
            image_files.append(bg_image)
            
    # 4. Lặp lại danh sách ảnh liên tục (Looping) cho đến khi phủ kín thời lượng audio thực tế!
    full_image_sequence = []
    accumulated_duration = 0.0
    idx = 0
    while accumulated_duration < (total_audio_duration if total_audio_duration > 0 else 60.0):
        img_item = image_files[idx % len(image_files)]
        full_image_sequence.append(img_item)
        accumulated_duration += interval
        idx += 1
        
    # 5. Tạo file danh sách FFmpeg concat
    concat_list_path = os.path.join(out_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for img in full_image_sequence:
            img_clean = os.path.abspath(img).replace("\\", "/")
            f.write(f"file '{img_clean}'\n")
            f.write(f"duration {interval}\n")
        # Dòng cuối lặp ảnh cuối cùng để tránh trôi frame
        if full_image_sequence:
            last_img_clean = os.path.abspath(full_image_sequence[-1]).replace("\\", "/")
            f.write(f"file '{last_img_clean}'\n")
            
    # 6. Định dạng bộ lọc Hiệu Ứng Di Chuyển Nhẹ Nhàng (Subtle Ken Burns Pan & Zoom Effect) + Phụ Đề Chuẩn YouTube
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path and os.path.exists(srt_path) else ""
    subtitle_style = "Fontname=Arial,FontSize=15,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,Outline=2,Shadow=1,Alignment=2,MarginV=35,MarginL=80,MarginR=80,WrapStyle=2"
    
    # Hiệu ứng Pan & Zoom di chuyển lên xuống nhẹ nhàng (Ken Burns Slow Motion: 25fps, d=interval*25 frames)
    frames_per_image = interval * 25
    kb_effect = (
        "scale=8000:-1,"
        f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+sin(time*0.5)*15':fps=25:d={frames_per_image}:s=1920x1080,"
        "crop=1920:1080,eq=brightness=-0.15:contrast=1.1[bg]"
    )
    
    if srt_escaped:
        vf_filter = f"{kb_effect};[bg]subtitles='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter = f"{kb_effect};[bg]null[out]"
        
    # 7. Chạy FFmpeg concat demuxer ghép nhạc + đổi ảnh từng phân cảnh
    codec = "libx264"
    try:
        test_nvenc = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=s=16x16:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True, timeout=5
        )
        if test_nvenc.returncode == 0:
            codec = "h264_nvenc"
            print("[INFO] GPU NVIDIA khả dụng! Tự động sử dụng phần cứng GPU NVENC...")
        else:
            print("[INFO] Sử dụng CPU H.264 Encoder (libx264)...")
    except Exception:
        codec = "libx264"

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-map", "[out]", "-map", "1:a",
        "-c:v", codec, "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-shortest", output_video_path
    ]
    
    try:
        print(f"[INFO] FFmpeg rendering full {total_audio_duration:.1f}s video slideshow with subtle Ken Burns motion...")
        # Tăng timeout lên 600s cho video dài 8-10 phút
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode == 0 and os.path.exists(output_video_path):
            print(f"[SUCCESS] Render video dài {total_audio_duration:.1f}s đầy đủ thành công: {output_video_path}")
            return output_video_path
        else:
            print(f"[WARNING] Concat slideshow warning: {res.stderr[:300]}")
    except Exception as e:
        print(f"[ERROR] Exception running FFmpeg slideshow: {e}")
        
    return ""

def render_novel_video(audio_path: str, srt_path: str, title: str, chapter_id: str) -> str:
    """Tự động render video từ audio & SRT (cứ 7 giây tự sinh 1 ảnh AI mới)."""
    out_video = os.path.join("output", chapter_id, "video.mp4")
    return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7)

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
