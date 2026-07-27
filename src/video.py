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

def create_multi_image_slideshow_video(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel", interval: int = 7) -> str:
    """Tự động sinh ảnh AI cứ mỗi 5-10 giây và ghép thành video slideshow chuyển cảnh sinh động 100% Free."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg không được cài đặt!")
        return ""
        
    out_dir = os.path.dirname(output_video_path)
    img_dir = os.path.join(out_dir, "scenes")
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Phân đoạn cảnh từ SRT
    scenes = parse_srt_scenes(srt_path, interval_seconds=interval)
    print(f"[INFO] Tổng số phân cảnh cần sinh ảnh AI (mỗi {interval}s đổi ảnh): {len(scenes)}")
    
    # 2. Sinh ảnh AI cho từng phân cảnh (tự động đính kèm Visual Memory 50-Feature)
    image_files = []
    for idx, scene_text in enumerate(scenes[:30]): # Giới hạn tối đa 30 ảnh cho mỗi tập
        img_path = os.path.join(img_dir, f"scene_{idx + 1:03d}.jpg")
        if not os.path.exists(img_path) or os.path.getsize(img_path) < 1000:
            print(f"[INFO] Sinh ảnh AI cảnh {idx + 1}/{len(scenes)}: {scene_text[:50]}...")
            generate_scene_image(f"{title}: {scene_text}", img_path, width=1920, height=1080)
            
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
            image_files.append(img_path)
            
    if not image_files:
        # Fallback ảnh gốc nếu lỗi
        bg_image = os.path.join(out_dir, "background.jpg")
        generate_scene_image(title, bg_image, width=1920, height=1080)
        image_files.append(bg_image)
        
    # 3. Tạo file danh sách FFmpeg concat
    concat_list_path = os.path.join(out_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for img in image_files:
            img_clean = os.path.abspath(img).replace("\\", "/")
            f.write(f"file '{img_clean}'\n")
            f.write(f"duration {interval}\n")
        # Lặp lại ảnh cuối
        if image_files:
            f.write(f"file '{os.path.abspath(image_files[-1]).replace('\\', '/')}'\n")
            
    # 4. Định dạng phụ đề chuẩn: Chữ Trắng (&H00FFFFFF&), Viền Đen Mỏng (Outline=1), Cỡ chữ vừa nhỏ (FontSize=16), 1 hàng (WrapStyle=2)
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path and os.path.exists(srt_path) else ""
    subtitle_style = "FontSize=16,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,Outline=1,Shadow=0,Alignment=2,MarginV=35,WrapStyle=2"
    
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=-0.15:contrast=1.1[bg]"
    if srt_escaped:
        vf_filter += f";[bg]subtitles='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    # 5. Chạy FFmpeg concat demuxer ghép nhạc + đổi ảnh mỗi 7s
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-map", "[out]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-shortest", output_video_path
    ]
    
    try:
        print(f"[INFO] FFmpeg rendering multi-image video slideshow (Cứ {interval}s đổi 1 ảnh)...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if res.returncode == 0 and os.path.exists(output_video_path):
            print(f"[SUCCESS] Render video đa ảnh AI thành công: {output_video_path}")
            return output_video_path
        else:
            print(f"[WARNING] Concat slideshow warning: {res.stderr[:200]}")
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
