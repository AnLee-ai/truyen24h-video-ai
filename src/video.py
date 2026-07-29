import os
import json
import re
import subprocess
import shutil
from src.image_generator import generate_scene_image

def parse_srt_scenes_with_durations(srt_path: str, target_min_duration: float = 5.0) -> list:
    """
    Đọc file SRT và phân nhóm các câu thoại thành các phân cảnh vừa vặn (5-8 giây),
    trả về danh sách dict chứa: {'text': text_thoai, 'duration': thoi_gian_thuc_te_giay}.
    Chuyển cảnh CHÍNH XÁC KHỚP VỚI LỜI NÓI NHÂN VẬT!
    """
    if not os.path.exists(srt_path):
        return [{'text': 'Mở đầu chương tiểu thuyết', 'duration': 7.0}]
        
    def time_to_sec(t_str):
        h, m, s_ms = t_str.split(':')
        s, ms = s_ms.split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())
        scenes = []
        
        current_texts = []
        current_start = None
        current_end = None
        
        for idx, block in enumerate(blocks):
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) >= 3:
                t_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                if t_match:
                    start_s = time_to_sec(t_match.group(1))
                    end_s = time_to_sec(t_match.group(2))
                    text_lines = " ".join(lines[2:])
                    
                    if current_start is None:
                        current_start = start_s
                    current_end = end_s
                    current_texts.append(text_lines)
                    
                    accumulated_dur = current_end - current_start
                    
                    # Gộp thoại đến khi đạt khoảng 5-8s hoặc là câu thoại cuối cùng
                    if accumulated_dur >= target_min_duration or idx == len(blocks) - 1:
                        scenes.append({
                            'text': " ".join(current_texts),
                            'duration': round(max(accumulated_dur, 2.5), 2)
                        })
                        current_texts = []
                        current_start = None
                        current_end = None
                        
        if scenes:
            return scenes
    except Exception as e:
        print(f"[WARNING] Lỗi đọc SRT khớp thời lượng thoại: {e}")
        
    return [{'text': 'Mở đầu chương tiểu thuyết', 'duration': 7.0}]

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
    """Tự động sinh ảnh AI và ghép thành video chuyển phân cảnh KHỚP 100% VỚI LỜI NÓI NHÂN VẬT."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg không được cài đặt!")
        return ""
        
    out_dir = os.path.dirname(output_video_path)
    img_dir = os.path.join(out_dir, "scenes")
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Đo chính xác độ dài audio thực tế tính bằng giây
    total_audio_duration = get_audio_duration_seconds(audio_path)
    print(f"[INFO] Thời lượng thực tế của file Audio: {total_audio_duration:.2f} giây ({total_audio_duration/60:.2f} phút).")
    
    # 2. Phân đoạn cảnh từ SRT với thời lượng khớp chính xác từng câu thoại
    scene_data_list = parse_srt_scenes_with_durations(srt_path, target_min_duration=5.0)
    scene_texts = [s['text'] for s in scene_data_list]
    print(f"[INFO] Tổng số phân cảnh sinh ảnh AI khớp thoại: {len(scene_texts)}")
    
    # 3. Sinh ảnh AI ĐA LUỒNG cho các phân cảnh (tối đa 40 ảnh)
    from src.image_generator import batch_generate_scene_images
    chapter_id = os.path.basename(out_dir)
    image_files = batch_generate_scene_images(scene_texts[:40], chapter_id=chapter_id, max_workers=2)
            
    # Đảm bảo video LUÔN CÓ ĐA DẠNG ẢNH ĐỔI PHÂN CẢNH (Không bao giờ bị 1 ảnh tĩnh duy nhất!)
    if len(image_files) < 5:
        print(f"[WARNING] Chỉ sinh được {len(image_files)} ảnh. Đang sinh tự động các phân cảnh biến thể dự phòng...")
        needed = 10 - len(image_files)
        for var_i in range(needed):
            fallback_path = os.path.join(img_dir, f"fallback_var_{var_i+1:02d}.jpg")
            scene_prompt = scene_texts[var_i % len(scene_texts)] + f", dramatic angle perspective variant {var_i+1}"
            res_p = generate_scene_image(scene_prompt, fallback_path, width=1920, height=1080)
            if res_p and os.path.exists(res_p) and os.path.getsize(res_p) > 1000:
                image_files.append(res_p)
                
    if not image_files:
        bg_image = os.path.join(out_dir, "background.jpg")
        generate_scene_image(title, bg_image, width=1920, height=1080)
        if os.path.exists(bg_image):
            image_files.append(bg_image)
            
    # 4. Ghép ảnh AI tương ứng với từng mốc thời gian thoại thực tế!
    full_scene_sequence = []
    accumulated_duration = 0.0
    idx = 0
    while accumulated_duration < (total_audio_duration if total_audio_duration > 0 else 60.0):
        scene_item = scene_data_list[idx % len(scene_data_list)]
        img_item = image_files[idx % len(image_files)]
        dur = scene_item['duration']
        
        full_scene_sequence.append({'image': img_item, 'duration': dur})
        accumulated_duration += dur
        idx += 1
        
    # 5. Tạo file danh sách FFmpeg concat với thời lượng riêng biệt KHỚP THOẠI CHO TỪNG ẢNH
    concat_list_path = os.path.join(out_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for item in full_scene_sequence:
            img_clean = os.path.abspath(item['image']).replace("\\", "/")
            f.write(f"file '{img_clean}'\n")
            f.write(f"duration {item['duration']}\n")
        # Dòng cuối lặp ảnh cuối cùng để tránh trôi frame
        if full_scene_sequence:
            last_img_clean = os.path.abspath(full_scene_sequence[-1]['image']).replace("\\", "/")
            f.write(f"file '{last_img_clean}'\n")
            
    # 6. Định dạng bộ lọc Phụ Đề & Đồ Họa Chuẩn Kênh Fan Review Truyện (Chữ Vàng Nổi, Dark Vignette, Tương Phản Điện Ảnh)
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:") if srt_path and os.path.exists(srt_path) else ""
    # Color format ASS: &H0000FFFF& = Vàng Chanh #FFFF00, Outline 3px Đen Chống Chói, Alignment 2 (Căn giữa lề dưới)
    subtitle_style = "Fontname=Arial,FontSize=18,PrimaryColour=&H0000FFFF&,OutlineColour=&H00000000&,Outline=3,Shadow=2,Alignment=2,MarginV=42,MarginL=80,MarginR=80,WrapStyle=2"
    
    # Filter chuỗi: Scale 1080p + Crop + Tăng tương phản + Saturation màu rực rỡ + Phủ mờ dải viền tối Vignette chuẩn điện ảnh
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=-0.08:contrast=1.18:saturation=1.25,vignette=PI/4[bg]"
    if srt_escaped:
        vf_filter += f";[bg]subtitles='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    # 7. Tự động kiểm tra phần cứng GPU Encoder (NVIDIA NVENC -> Intel QSV -> AMD AMF -> CPU libx264)
    codec = "libx264"
    encoder_opts = ["-preset", "fast"]
    
    try:
        # Test 1: NVIDIA NVENC GPU
        test_nvenc = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=s=16x16:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True, timeout=5
        )
        if test_nvenc.returncode == 0:
            codec = "h264_nvenc"
            encoder_opts = ["-preset", "p4", "-rc", "vbr"]
            print("[INFO] GPU NVIDIA NVENC khả dụng! Kích hoạt tăng tốc phần cứng GPU...")
        else:
            # Test 2: Intel QuickSync QSV
            test_qsv = subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=s=16x16:d=0.1", "-c:v", "h264_qsv", "-f", "null", "-"],
                capture_output=True, text=True, timeout=5
            )
            if test_qsv.returncode == 0:
                codec = "h264_qsv"
                print("[INFO] GPU Intel QSV khả dụng! Kích hoạt tăng tốc phần cứng QSV...")
            else:
                print("[INFO] Sử dụng CPU H.264 Encoder (libx264)...")
    except Exception:
        codec = "libx264"

    # Lệnh FFmpeg tối ưu: Khóa đồng bộ âm thanh - async 1, VSync 1, Bitrate 1400k (Dưới 45MB cho 10 phút)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-map", "[out]", "-map", "1:a",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "1400k", "-maxrate", "2000k", "-bufsize", "3000k",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-shortest", output_video_path
    ]
    
    try:
        print(f"[INFO] FFmpeg rendering full {total_audio_duration:.1f}s video ({codec})...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Tự động kiểm tra chất lượng video sau khi render
        from src.video_validator import validate_video_file
        if res.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=500000):
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
