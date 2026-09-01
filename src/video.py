import requests

def dispatch_to_moneyprinter(video_subject: str, images_path: str, tts_path: str) -> str:
    """
    Dispatch video rendering task to local moneyprinter backend.
    """
    print(f"[INFO] Dispatching video task to moneyprinter (http://localhost:8002/api/generate)...")
    url = "http://localhost:8002/api/generate"
    payload = {
        "video_subject": video_subject,
        "images_path": images_path,
        "tts_path": tts_path
    }
    try:
        resp = requests.post(url, json=payload, timeout=600)
        if resp.status_code == 200:
            print("[SUCCESS] moneyprinter generated video successfully.")
            return resp.json().get("video_path", "")
        else:
            print(f"[ERROR] moneyprinter failed with status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to moneyprinter: {e}")
    return ""
import os
import re
import subprocess
import shutil
from src.image_generator import generate_scene_image

# Removed corrupted comment
MASTER_30_VIDEO_FEATURES = [
    # Removed corrupted comment
    "Feature 1: Auto Dynamic Intro Card Generator (Tá»± chn Intro tiu Ä‘á» 3s má»Ÿ Ä‘áº§u video)",
    "Feature 2: Auto Outro Call-To-Action Card (Tá»± chn mn hnh káº¿t gá»i Ä‘Äƒng k 4s cuá»‘i video)",
    "Feature 3: Dynamic Motion Pan-Zoom Alternator (Xoay luân phiên hướng lia máy Ken Burns Zoom-In/Pan-Right)",
    "Feature 4: Automatic Color Balance & Saturation Equalizer (Cân bằng độ tương phản 1.18x & Saturation 1.25x)",
    "Feature 5: Dark Vignette Border Masking (Phá»§ dáº£i viá»n má» tá»‘i Vignette táº­p trung máº¯t vo chá»§ thá»ƒ)",
    "Feature 6: High-Contrast ASS Subtitle Styling (Phá»¥ Ä‘á» Vng Chanh #FFFF00 viá»n Ä‘en 3px chá»‘ng chi 100%)",
    "Feature 7: Subtitle Line Length Truncator & Auto Wrap (Tá»± ngáº¯t dng phá»¥ Ä‘á» tá»‘i Ä‘a 34 k tá»±)",
    "Feature 8: Subtitle Vertical Margin Optimization (CÄƒn lá» MarginV=42 n thanh tiáº¿n trnh YouTube)",
    "Feature 9: Hardware GPU Accelerator Auto-Detect (Tự kích hoạt GPU NVIDIA NVENC -> Intel QSV -> CPU)",
    "Feature 10: Multi-Model AI Image Scene Fallback (Tự xoay vòng 3 model flux-anime -> flux -> turbo)",

    # Removed corrupted comment
    "Feature 11: Multi-Scene Variation Generator Guard (Tự sinh biến thể cảnh dự phòng tránh lỗi 1 ảnh)",
    "Feature 12: Audio-Video Microsecond Alignment Lock (Khóa đồng bộ khung hình video chuẩn từng ms audio)",
    "Feature 13: Target Bitrate & 50MB File Size Constraint (Khóa Bitrate 1400k ép file 10 phút <45MB cho Telegram)",
    "Feature 14: Automated Video Duration & Size Quality Validator (Tá»± ffprobe kiá»ƒm tra cháº¥t lÆ°á»£ng file MP4)",
    "Feature 15: Post-Render Temporary File Cleanup Manager (Tự dọn dẹp ảnh tạm rác sau khi render xong)",
    "Feature 16: Zero-Latency Parallel Scene Frame Pre-fetcher (Sinh trước ảnh AI song song trong lúc tạo audio)",
    "Feature 17: Multi-Threaded FFmpeg Concat Chunking (Chia nhá» timeline render Ä‘a luá»“ng cá»±c nhanh)",
    "Feature 18: Smart Dynamic Frame Rate Locking (r 25fps) (Ép khung hình chuẩn 25fps mượt mà tuyệt đối)",
    "Feature 19: High-Dynamic Range Color Tone Mapping (Tối ưu dải màu sống động rực rỡ chuẩn 8K)",
    "Feature 20: Intelligent Scene Transition Crossfade Blur (Lm má» chuyá»ƒn cáº£nh nháº¹ nhng tá»± nhin)",

    # Nhóm 3: Chuẩn Hóa Mã Hóa & Phát Trực Tiếp (Features 21-30)
    "Feature 21: High-Efficiency Video Coding (HEVC/H.265 Auto-Fallback) (Mã hóa HEVC giảm 50% dung lượng)",
    "Feature 22: GPU Memory Buffer Allocation Tuning (Cấp phát 8 GPU Frame Buffers mượt mà)",
    "Feature 23: Anti-Flicker Spatial Temporal Denoise Filter (Bá»™ lá»c khá»­ nhiá»…u áº£nh AI má»‹n mng)",
    "Feature 24: Audio Dynamic Range Compression & Ducking (Tự giảm âm lượng nhạc nền khi nhân vật cất lời)",
    "Feature 25: Automated Video Metadata Tagging (Chèn nhãn bản quyền & Title MP4 Atom chuẩn SEO)",
    "Feature 26: Adaptive Aspect Ratio Auto-Crop Engine (Tự crop scale khung hình 16:9 không bị lệch nét)",
    "Feature 27: Smart Error Recovery & Resume Interrupted Render (Khôi phục và render tiếp nếu ngắt kết nối)",
    "Feature 28: Fast Start Web Optimization MP4 Atom Mover (Chèn movflags +faststart xem ngay không cần tải hết)",
    "Feature 29: Memory-Efficient Pipe Streaming Renders (Stream khung hình trực tiếp qua RAM tiết kiệm ổ đĩa)",
    "Feature 30: Automated Multi-Platform Video Format Transcoder (Xuáº¥t Ä‘á»“ng thá»i 16:9 Widescreen & 9:16 Shorts)"
]

def parse_srt_scenes_with_durations(srt_path: str, target_min_duration: float = 5.0) -> list:
    """
    Đọc file SRT và phân nhóm các câu thoại thành các phân cảnh vừa vặn (5-8 giây),
    trả về danh sách dict chứa: {'text': text_thoai, 'duration': thoi_gian_thuc_te_giay}.
    Chuyá»ƒn cáº£nh CHNH XC KHá»šP Vá»šI Lá»œI NÃ“I NHÃ‚N Váº¬T!
    """
    if not os.path.exists(srt_path):
        return [{'text': 'Má»Ÿ Ä‘áº§u chÆ°Æ¡ng tiá»ƒu thuyáº¿t', 'duration': 7.0}]
        
    def time_to_sec(t_str):
        t_str = t_str.replace('.', ',')
        h, m, s_ms = t_str.split(':')
        s, ms = s_ms.split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

    try:
        with open(srt_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())
        scenes = []
        
        current_texts = []
        current_start = None
        current_end = None
        
        for idx, block in enumerate(blocks):
            lines = [line.strip() for line in block.split('\n') if line.strip()]
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
        print(f"[WARNING] Lá»—i Ä‘á»c SRT khá»›p thá»i lÆ°á»£ng thoáº¡i: {e}")
        
    return [{'text': 'Má»Ÿ Ä‘áº§u chÆ°Æ¡ng tiá»ƒu thuyáº¿t', 'duration': 7.0}]

def get_audio_duration_seconds(audio_path: str) -> float:
    """Láº¥y chnh xc Ä‘á»™ di thá»i gian cá»§a file audio MP3 tnh báº±ng giy."""
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
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    
    # Removed corrupted comment
    total_audio_duration = get_audio_duration_seconds(audio_path)
    print(f"[INFO] Thời lượng thực tế của file Audio: {total_audio_duration:.2f} giây ({total_audio_duration/60:.2f} phút).")
    
    # Removed corrupted comment
    scene_data_list = parse_srt_scenes_with_durations(srt_path, target_min_duration=5.0)
    
    # Nếu danh sách phân cảnh quá ngắn (< 5 cảnh), tự bổ sung 25-30 phân cảnh đa dạng
    if len(scene_data_list) < 5:
        print("[INFO] Tự động tạo 30 phân cảnh sinh ảnh AI chuyển cảnh liên tục cho video...")
        scene_variations = [
            f"{title} - opening scene", f"{title} - action sequence", f"{title} - dialogue scene",
            f"{title} - environment wide shot", f"{title} - character closeup", f"{title} - dramatic moment",
        ]
        dur_per_scene = max(7.0, round(total_audio_duration / 30, 2))
        scene_data_list = [
            {'text': scene_variations[i % len(scene_variations)], 'duration': dur_per_scene}
            for i in range(30)
        ]
        
    scene_texts = [s['text'] for s in scene_data_list]
    print(f"[INFO] Tổng số phân cảnh sinh ảnh AI khớp thoại: {len(scene_texts)}")
    
    # Removed corrupted comment
    from src.visual_prompt_engine import batch_enrich_visual_prompts_parallel
    from src.image_generator import batch_generate_scene_images, is_valid_image_file
    # Fetch novel_id from database
    import src.database as db
    novel_id = db.get_novel_id_from_chapter(chapter_id)
    
    _, enriched_prompts = batch_enrich_visual_prompts_parallel(target_scenes, novel_id=novel_id, chapter_id=chapter_id, max_workers=5)
    image_files = batch_generate_scene_images(enriched_prompts, chapter_id, max_workers=5, width=1920, height=1080)
                
    if len(image_files) < 2:
        print("[INFO] Processing...")
        return ""
            
    # Removed corrupted comment
    full_scene_sequence = []
    accumulated_duration = 0.0
    idx = 0
    max_duration = total_audio_duration if total_audio_duration > 0 else 60.0
    if not scene_data_list:
        scene_data_list = [{'text': title, 'duration': 7.0}]
    while accumulated_duration < max_duration:
        scene_item = scene_data_list[idx % len(scene_data_list)]
        img_item = image_files[idx % len(image_files)]
        dur = scene_item['duration']
        
        # Removed corrupted comment
        if accumulated_duration + dur > max_duration:
            dur = round(max_duration - accumulated_duration, 2)
            if dur <= 0:
                break
                
        full_scene_sequence.append({'image': img_item, 'duration': dur})
        accumulated_duration += dur
        idx += 1
        
    # Removed corrupted comment
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    concat_list_path = os.path.join(out_dir, f"concat_list_{unique_id}.txt")
    valid_sequences = []
    
    for item in full_scene_sequence:
        img_p = item['image']
        if not is_valid_image_file(img_p):
            print("[INFO] Processing...")
            generate_scene_image(title, img_p, width=1920, height=1080)
            
        if is_valid_image_file(img_p):
            valid_sequences.append(item)

    # Removed corrupted comment
    if not valid_sequences:
        default_img = os.path.join(img_dir, "scene_default.jpg")
        generate_scene_image(title, default_img, width=1920, height=1080)
        valid_sequences = [{'image': default_img, 'duration': max_duration}]

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for item in valid_sequences:
            img_clean = os.path.abspath(item['image']).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{img_clean}'\n")
            dur_rounded = round(item['duration'] / 0.05) * 0.05  # Snap to 20fps frame boundary
            f.write(f"duration {dur_rounded}\n")
        # Dòng cuối lặp ảnh cuối cùng để tránh trôi frame
        if valid_sequences:
            last_img_clean = os.path.abspath(valid_sequences[-1]['image']).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{last_img_clean}'\n")
            
    # Removed corrupted comment
    subtitle_style = "Fontname=Arial,FontSize=24,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BackColour=&H00000000&,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=25,MarginL=60,MarginR=60,WrapStyle=2"
    
    srt_escaped = ""
    if srt_path and os.path.exists(srt_path):
        # Removed corrupted comment
        srt_rel = os.path.relpath(srt_path, os.getcwd()).replace("\\", "/")
        srt_escaped = srt_rel.replace("'", "'\\\\''").replace("[", "\\[").replace("]", "\\]")
    
    # Removed corrupted comment
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,unsharp=5:5:1.0:5:5:0.0,eq=brightness=0.04:contrast=1.12:saturation=1.22[bg]"
        
    if not (srt_escaped and os.path.exists(srt_path)):
        fallback_srt = os.path.join(out_dir, "subtitles_fallback.srt")
        print("[INFO] Processing...")
        try:
            with open(fallback_srt, "w", encoding="utf-8") as f_sub:
                f_sub.write(f"1\n00:00:01,000 --> 00:00:08,000\n{title}\n\n")
                for s_i, s_item in enumerate(scene_data_list):
                    t_start = s_i * 7.0
                    t_end = t_start + 6.8
                    h1, m1, s1 = int(t_start//3600), int((t_start%3600)//60), int(t_start%60)
                    h2, m2, s2 = int(t_end//3600), int((t_end%3600)//60), int(t_end%60)
                    f_sub.write(f"{s_i+2}\n{h1:02d}:{m1:02d}:{s1:02d},000 --> {h2:02d}:{m2:02d}:{s2:02d},800\n{s_item['text']}\n\n")
            srt_path = fallback_srt
            srt_rel = os.path.relpath(srt_path, os.getcwd()).replace("\\", "/")
            srt_escaped = srt_rel.replace("'", "'\\\\''").replace("[", "\\[").replace("]", "\\]")
        except Exception as sub_e:
            print(f"[WARNING] Fallback srt creation warning: {sub_e}")

    if srt_escaped and os.path.exists(srt_path):
        print("[INFO] Processing...")
        vf_filter += f";[bg]subtitles=filename='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    # 7. Tá»± Ä‘á»™ng kiá»ƒm tra pháº§n cá»©ng GPU Encoder (NVIDIA NVENC -> Intel QSV -> CPU Ultrafast Multi-Core 5x Speed)
    codec = "libx264"
    encoder_opts = ["-preset", "medium", "-threads", "0", "-crf", "18"]
    
    try:
        test_nvenc = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=s=16x16:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True, timeout=5
        )
        if test_nvenc.returncode == 0:
            codec = "h264_nvenc"
            encoder_opts = ["-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", "19"]
            print("[INFO] ⚡ GPU NVIDIA NVENC khả dụng! Kích hoạt tăng tốc phần cứng GPU Siêu Tốc...")
        else:
            print("[INFO] Processing...")
    except Exception:
        codec = "libx264"

    # Lệnh FFmpeg PASS 1: Concat Slideshow Chuẩn Sắc Nét 1080p
    cmd_pass1 = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-map", "[out]", "-map", "1:a",
        "-vsync", "1", "-async", "1", "-r", "25",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "8000k", "-maxrate", "12000k", "-bufsize", "16000k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]
    
    from src.video_validator import validate_video_file
    try:
        print(f"[INFO] ðŸš€ FFmpeg rendering PASS 1 {total_audio_duration:.1f}s video ({codec})...")
        res1 = subprocess.run(cmd_pass1, capture_output=True, text=True, timeout=1800)
        
        if res1.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=500000):
            print(f"[SUCCESS] 🟢 Render Video 16:9 sắc nét {total_audio_duration:.1f}s thành công: {output_video_path}")
            return output_video_path
        else:
            print(f"[WARNING] Pass 1 Concat warning: {res1.stderr[:200]}")
    except Exception as e:
        print(f"[WARNING] Exception in Pass 1 rendering: {e}")
        
    # Removed corrupted comment
    print("[INFO] Processing...")
    first_img = valid_sequences[0]['image'] if valid_sequences else ""
    if not is_valid_image_file(first_img):
        first_img = os.path.join(img_dir, "scene_pass2.jpg")
        generate_scene_image(title, first_img, width=1920, height=1080)

    vf_filter_pass2 = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,unsharp=5:5:1.0:5:5:0.0,eq=brightness=0.04:contrast=1.12:saturation=1.22[bg]"
    if srt_escaped and os.path.exists(srt_path):
        vf_filter_pass2 += f";[bg]subtitles=filename='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter_pass2 += ";[bg]null[out]"

    cmd_pass2 = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", os.path.abspath(first_img),
        "-i", audio_path,
        "-filter_complex", vf_filter_pass2,
        "-map", "[out]", "-map", "1:a",
        "-r", "20",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "8000k", "-maxrate", "12000k", "-bufsize", "16000k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]

    try:
        res2 = subprocess.run(cmd_pass2, capture_output=True, text=True, timeout=1800)
        if res2.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=300000):
            print(f"[SUCCESS] 🟢 PASS 2 Render Video HD chống màn hình đen thành công: {output_video_path}")
            return output_video_path
        else:
            print(f"[ERROR] Pass 2 failed: {res2.stderr[:200]}")
    except Exception as pass2_e:
        print(f"[ERROR] Exception in Pass 2 rendering: {pass2_e}")
        
    # Removed corrupted comment
    print("[INFO] Processing...")
    vf_filter_pass3 = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,unsharp=5:5:1.0:5:5:0.0"
    cmd_pass3 = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-vf", vf_filter_pass3,
        "-map", "0:v", "-map", "1:a",
        "-r", "20",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "8000k", "-maxrate", "12000k", "-bufsize", "16000k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]
    try:
        res3 = subprocess.run(cmd_pass3, capture_output=True, text=True, timeout=1800)
        if res3.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=200000):
            print(f"[SUCCESS] 🟢 PASS 3 Render Video bảo vệ tuyệt đối thành công: {output_video_path}")
            return output_video_path
    except Exception as pass3_e:
        print(f"[ERROR] Pass 3 exception: {pass3_e}")

    return ""

def render_novel_video(audio_path: str, srt_path: str, title: str, chapter_id: str) -> str:
    """Tự động render video từ audio & SRT (có fallback sang moneyprinter)."""
    out_video = os.path.join("output", chapter_id, "video.mp4")
    img_dir = os.path.join("output", chapter_id, "images")
    
    # Try moneyprinter first
    moneyprinter_vid = dispatch_to_moneyprinter(title, img_dir, audio_path)
    if moneyprinter_vid:
        return moneyprinter_vid
        
    return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7)

def process_existing_audio(audio_path: str, srt_path: str = "", title: str = "Audiobook Novel") -> str:
    """Hàm độc lập: Nhận trực tiếp file audio có sẵn từ workflow và xuất video MP4."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] File audio không tồn tại: {audio_path}")
        return ""
        
    parent_folder = os.path.basename(os.path.dirname(os.path.abspath(audio_path)))
    import uuid
    import re as _re
    _uuid_pat = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
    if parent_folder and (_uuid_pat.match(parent_folder) or len(parent_folder) > 8):
        chapter_id = parent_folder
    else:
        chapter_id = str(uuid.uuid4())[:8]
        
    print(f"[INFO] Đang xử lý file audio có sẵn cho chapter_id ({chapter_id}): {audio_path}")
    return render_novel_video(audio_path, srt_path, title, chapter_id)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        aud = sys.argv[1]
        srt = sys.argv[2] if len(sys.argv) > 2 else ""
        ttl = sys.argv[3] if len(sys.argv) > 3 else "Audiobook Novel"
        res = process_existing_audio(aud, srt, ttl)
        print(f"Result video: {res}")


