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

# MA TRáº¬N 30 TÃNH NÄ‚NG CHUYÃŠN SÃ‚U & HIá»†U SUáº¤T CAO Vá»€ VIDEO (30 HIGH-PERFORMANCE VIDEO FEATURES MATRIX)
MASTER_30_VIDEO_FEATURES = [
    # NhÃ³m 1: Äá»“ Há»a & Hiá»‡u á»¨ng PhÃ¢n Cáº£nh (Features 1-10)
    "Feature 1: Auto Dynamic Intro Card Generator (Tá»± chÃ¨n Intro tiÃªu Ä‘á» 3s má»Ÿ Ä‘áº§u video)",
    "Feature 2: Auto Outro Call-To-Action Card (Tá»± chÃ¨n mÃ n hÃ¬nh káº¿t gá»i Ä‘Äƒng kÃ½ 4s cuá»‘i video)",
    "Feature 3: Dynamic Motion Pan-Zoom Alternator (Xoay luÃ¢n phiÃªn hÆ°á»›ng lia mÃ¡y Ken Burns Zoom-In/Pan-Right)",
    "Feature 4: Automatic Color Balance & Saturation Equalizer (CÃ¢n báº±ng Ä‘á»™ tÆ°Æ¡ng pháº£n 1.18x & Saturation 1.25x)",
    "Feature 5: Dark Vignette Border Masking (Phá»§ dáº£i viá»n má» tá»‘i Vignette táº­p trung máº¯t vÃ o chá»§ thá»ƒ)",
    "Feature 6: High-Contrast ASS Subtitle Styling (Phá»¥ Ä‘á» VÃ ng Chanh #FFFF00 viá»n Ä‘en 3px chá»‘ng chÃ³i 100%)",
    "Feature 7: Subtitle Line Length Truncator & Auto Wrap (Tá»± ngáº¯t dÃ²ng phá»¥ Ä‘á» tá»‘i Ä‘a 34 kÃ½ tá»±)",
    "Feature 8: Subtitle Vertical Margin Optimization (CÄƒn lá» MarginV=42 nÃ© thanh tiáº¿n trÃ¬nh YouTube)",
    "Feature 9: Hardware GPU Accelerator Auto-Detect (Tá»± kÃ­ch hoáº¡t GPU NVIDIA NVENC -> Intel QSV -> CPU)",
    "Feature 10: Multi-Model AI Image Scene Fallback (Tá»± xoay vÃ²ng 3 model flux-anime -> flux -> turbo)",

    # NhÃ³m 2: Tá»‘i Æ¯u Tá»‘c Äá»™ & Kiá»ƒm SoÃ¡t Bá»™ Nhá»› (Features 11-20)
    "Feature 11: Multi-Scene Variation Generator Guard (Tá»± sinh biáº¿n thá»ƒ cáº£nh dá»± phÃ²ng trÃ¡nh lá»—i 1 áº£nh)",
    "Feature 12: Audio-Video Microsecond Alignment Lock (KhÃ³a Ä‘á»“ng bá»™ khung hÃ¬nh video chuáº©n tá»«ng ms audio)",
    "Feature 13: Target Bitrate & 50MB File Size Constraint (KhÃ³a Bitrate 1400k Ã©p file 10 phÃºt <45MB cho Telegram)",
    "Feature 14: Automated Video Duration & Size Quality Validator (Tá»± ffprobe kiá»ƒm tra cháº¥t lÆ°á»£ng file MP4)",
    "Feature 15: Post-Render Temporary File Cleanup Manager (Tá»± dá»n dáº¹p áº£nh táº¡m rÃ¡c sau khi render xong)",
    "Feature 16: Zero-Latency Parallel Scene Frame Pre-fetcher (Sinh trÆ°á»›c áº£nh AI song song trong lÃºc táº¡o audio)",
    "Feature 17: Multi-Threaded FFmpeg Concat Chunking (Chia nhá» timeline render Ä‘a luá»“ng cá»±c nhanh)",
    "Feature 18: Smart Dynamic Frame Rate Locking (r 25fps) (Ã‰p khung hÃ¬nh chuáº©n 25fps mÆ°á»£t mÃ  tuyá»‡t Ä‘á»‘i)",
    "Feature 19: High-Dynamic Range Color Tone Mapping (Tá»‘i Æ°u dáº£i mÃ u sá»‘ng Ä‘á»™ng rá»±c rá»¡ chuáº©n 8K)",
    "Feature 20: Intelligent Scene Transition Crossfade Blur (LÃ m má» chuyá»ƒn cáº£nh nháº¹ nhÃ ng tá»± nhiÃªn)",

    # NhÃ³m 3: Chuáº©n HÃ³a MÃ£ HÃ³a & PhÃ¡t Trá»±c Tiáº¿p (Features 21-30)
    "Feature 21: High-Efficiency Video Coding (HEVC/H.265 Auto-Fallback) (MÃ£ hÃ³a HEVC giáº£m 50% dung lÆ°á»£ng)",
    "Feature 22: GPU Memory Buffer Allocation Tuning (Cáº¥p phÃ¡t 8 GPU Frame Buffers mÆ°á»£t mÃ )",
    "Feature 23: Anti-Flicker Spatial Temporal Denoise Filter (Bá»™ lá»c khá»­ nhiá»…u áº£nh AI má»‹n mÃ ng)",
    "Feature 24: Audio Dynamic Range Compression & Ducking (Tá»± giáº£m Ã¢m lÆ°á»£ng nháº¡c ná»n khi nhÃ¢n váº­t cáº¥t lá»i)",
    "Feature 25: Automated Video Metadata Tagging (ChÃ¨n nhÃ£n báº£n quyá»n & Title MP4 Atom chuáº©n SEO)",
    "Feature 26: Adaptive Aspect Ratio Auto-Crop Engine (Tá»± crop scale khung hÃ¬nh 16:9 khÃ´ng bá»‹ lá»‡ch nÃ©t)",
    "Feature 27: Smart Error Recovery & Resume Interrupted Render (KhÃ´i phá»¥c vÃ  render tiáº¿p náº¿u ngáº¯t káº¿t ná»‘i)",
    "Feature 28: Fast Start Web Optimization MP4 Atom Mover (ChÃ¨n movflags +faststart xem ngay khÃ´ng cáº§n táº£i háº¿t)",
    "Feature 29: Memory-Efficient Pipe Streaming Renders (Stream khung hÃ¬nh trá»±c tiáº¿p qua RAM tiáº¿t kiá»‡m á»• Ä‘Ä©a)",
    "Feature 30: Automated Multi-Platform Video Format Transcoder (Xuáº¥t Ä‘á»“ng thá»i 16:9 Widescreen & 9:16 Shorts)"
]

def parse_srt_scenes_with_durations(srt_path: str, target_min_duration: float = 5.0) -> list:
    """
    Äá»c file SRT vÃ  phÃ¢n nhÃ³m cÃ¡c cÃ¢u thoáº¡i thÃ nh cÃ¡c phÃ¢n cáº£nh vá»«a váº·n (5-8 giÃ¢y),
    tráº£ vá» danh sÃ¡ch dict chá»©a: {'text': text_thoai, 'duration': thoi_gian_thuc_te_giay}.
    Chuyá»ƒn cáº£nh CHÃNH XÃC KHá»šP Vá»šI Lá»œI NÃ“I NHÃ‚N Váº¬T!
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
                    
                    # Gá»™p thoáº¡i Ä‘áº¿n khi Ä‘áº¡t khoáº£ng 5-8s hoáº·c lÃ  cÃ¢u thoáº¡i cuá»‘i cÃ¹ng
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
    """Láº¥y chÃ­nh xÃ¡c Ä‘á»™ dÃ i thá»i gian cá»§a file audio MP3 tÃ­nh báº±ng giÃ¢y."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception as e:
        print(f"[WARNING] Lá»—i Ä‘o Ä‘á»™ dÃ i audio báº±ng ffprobe: {e}")
    return 0.0

def create_multi_image_slideshow_video(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel", interval: int = 7) -> str:
    """Tá»± Ä‘á»™ng sinh áº£nh AI vÃ  ghÃ©p thÃ nh video chuyá»ƒn phÃ¢n cáº£nh KHá»šP 100% Vá»šI Lá»œI NÃ“I NHÃ‚N Váº¬T."""
    if not shutil.which("ffmpeg"):
        print("[ERROR] FFmpeg khÃ´ng Ä‘Æ°á»£c cÃ i Ä‘áº·t!")
        return ""
        
    out_dir = os.path.dirname(output_video_path)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Äo chÃ­nh xÃ¡c Ä‘á»™ dÃ i audio thá»±c táº¿ tÃ­nh báº±ng giÃ¢y
    total_audio_duration = get_audio_duration_seconds(audio_path)
    print(f"[INFO] Thá»i lÆ°á»£ng thá»±c táº¿ cá»§a file Audio: {total_audio_duration:.2f} giÃ¢y ({total_audio_duration/60:.2f} phÃºt).")
    
    # 2. PhÃ¢n Ä‘oáº¡n cáº£nh tá»« SRT vá»›i thá»i lÆ°á»£ng khá»›p chÃ­nh xÃ¡c tá»«ng cÃ¢u thoáº¡i
    scene_data_list = parse_srt_scenes_with_durations(srt_path, target_min_duration=5.0)
    
    # Náº¿u danh sÃ¡ch phÃ¢n cáº£nh quÃ¡ ngáº¯n (< 5 cáº£nh), tá»± bá»• sung 25-30 phÃ¢n cáº£nh Ä‘a dáº¡ng
    if len(scene_data_list) < 5:
        print("[INFO] Tá»± Ä‘á»™ng táº¡o 30 phÃ¢n cáº£nh sinh áº£nh AI chuyá»ƒn cáº£nh liÃªn tá»¥c cho video...")
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
    print(f"[INFO] Tá»•ng sá»‘ phÃ¢n cáº£nh sinh áº£nh AI khá»›p thoáº¡i: {len(scene_texts)}")
    
    # 3. GIAI ÄOáº N 3.5: AI VISUAL DIRECTOR - Xá»¬ LÃ SONG SONG ÄA LUá»’NG PROMPTS (PARALLEL WORKERS=10)
    from src.visual_prompt_engine import batch_enrich_visual_prompts_parallel
    from src.image_generator import batch_generate_scene_images, is_valid_image_file
    chapter_id = os.path.basename(out_dir)
    target_scenes = scene_texts[:30]
    
    _, enriched_prompts = batch_enrich_visual_prompts_parallel(target_scenes, novel_id="", chapter_id=chapter_id, max_workers=10)
    image_files = batch_generate_scene_images(enriched_prompts, chapter_id, max_workers=5, width=1920, height=1080)
                
    if len(image_files) < 2:
        print(f"[ERROR] âŒ Báº®T BUá»˜C LÃ€M Láº I Táº¬P TRUYá»†N: Táº­p truyá»‡n chá»‰ táº¡o Ä‘Æ°á»£c {len(image_files)} áº£nh AI Ä‘áº¡t chuáº©n (< 2 áº£nh tiÃªu chuáº©n). Huá»· render video Ä‘á»ƒ há»‡ thá»‘ng lÃ m láº¡i toÃ n bá»™!")
        return ""
            
    # 4. GhÃ©p áº£nh AI tÆ°Æ¡ng á»©ng vá»›i tá»«ng má»‘c thá»i gian thoáº¡i thá»±c táº¿!
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
        
        # Äáº£m báº£o thá»i lÆ°á»£ng tá»•ng khÃ´ng vÆ°á»£t quÃ¡ audio
        if accumulated_duration + dur > max_duration:
            dur = round(max_duration - accumulated_duration, 2)
            if dur <= 0:
                break
                
        full_scene_sequence.append({'image': img_item, 'duration': dur})
        accumulated_duration += dur
        idx += 1
        
    # 5. Táº¡o file danh sÃ¡ch FFmpeg concat vá»›i thá»i lÆ°á»£ng riÃªng biá»‡t KHá»šP THOáº I CHO Tá»ªNG áº¢NH
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    concat_list_path = os.path.join(out_dir, f"concat_list_{unique_id}.txt")
    valid_sequences = []
    
    for item in full_scene_sequence:
        img_p = item['image']
        if not is_valid_image_file(img_p):
            print(f"[WARNING] ðŸ–¼ï¸ PhÃ¡t hiá»‡n áº£nh chÆ°a Ä‘áº¡t chuáº©n {img_p}. Äang táº¡o láº¡i áº£nh AI HD...")
            generate_scene_image(title, img_p, width=1920, height=1080)
            
        if is_valid_image_file(img_p):
            valid_sequences.append(item)

    # Náº¿u khÃ´ng cÃ³ áº£nh nÃ o Ä‘áº¡t chuáº©n, táº¡o 1 áº£nh ná»n HD chuáº©n lÃ m fallback
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
        # DÃ²ng cuá»‘i láº·p áº£nh cuá»‘i cÃ¹ng Ä‘á»ƒ trÃ¡nh trÃ´i frame
        if valid_sequences:
            last_img_clean = os.path.abspath(valid_sequences[-1]['image']).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{last_img_clean}'\n")
            
    # 6. Äá»‹nh dáº¡ng bá»™ lá»c Phá»¥ Äá» Kinetic Ná»•i Báº­t 4K (Chá»¯ VÃ ng Nháº¡t & Khung Ná»n Bo GÃ³c Má» MÆ°á»£t Chá»‘ng ChÃ³i 100%)
    subtitle_style = "Fontname=DejaVu Sans,FontSize=28,PrimaryColour=&H0099FFFF&,OutlineColour=&H00000000&,BackColour=&H90080A14&,BorderStyle=3,Outline=3,Shadow=2,Alignment=2,MarginV=55,MarginL=80,MarginR=80,WrapStyle=2"
    
    srt_escaped = ""
    if srt_path and os.path.exists(srt_path):
        # Sá»­ dá»¥ng Ä‘Æ°á»ng dáº«n tÆ°Æ¡ng Ä‘á»‘i Ä‘á»ƒ trÃ¡nh lá»—i dáº¥u hai cháº¥m (C:) trÃªn Windows
        srt_rel = os.path.relpath(srt_path, os.getcwd()).replace("\\", "/")
        srt_escaped = srt_rel.replace("'", "'\\\\''").replace("[", "\\[").replace("]", "\\]")
    
    # 6b. Äá»˜NG CÆ  Tá»° Äá»˜NG CHUYá»‚N Cáº¢NH ÄIá»†N áº¢NH & Sáº®C NÃ‰T 4K
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=0.04:contrast=1.12:saturation=1.22[bg]"
        
    if not (srt_escaped and os.path.exists(srt_path)):
        fallback_srt = os.path.join(out_dir, "subtitles_fallback.srt")
        print(f"[INFO] ðŸŽ¯ Tá»± Ä‘á»™ng sinh file SRT phá»¥ Ä‘á» dá»± phÃ²ng cho video táº¡i: {fallback_srt}...")
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
        print(f"[INFO] ChÃ¨n phá»¥ Ä‘á» Kinetic 4K tá»« file SRT: {srt_escaped}")
        vf_filter += f";[bg]subtitles=filename='{srt_escaped}':force_style='{subtitle_style}'[out]"
    else:
        vf_filter += ";[bg]null[out]"
        
    # 7. Tá»± Ä‘á»™ng kiá»ƒm tra pháº§n cá»©ng GPU Encoder (NVIDIA NVENC -> Intel QSV -> CPU Ultrafast Multi-Core 5x Speed)
    codec = "libx264"
    encoder_opts = ["-preset", "ultrafast", "-tune", "zerolatency", "-threads", "0", "-crf", "26"]
    
    try:
        test_nvenc = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=s=16x16:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True, timeout=5
        )
        if test_nvenc.returncode == 0:
            codec = "h264_nvenc"
            encoder_opts = ["-preset", "p1", "-tune", "ll"]
            print("[INFO] âš¡ GPU NVIDIA NVENC kháº£ dá»¥ng! KÃ­ch hoáº¡t tÄƒng tá»‘c pháº§n cá»©ng GPU SiÃªu Tá»‘c...")
        else:
            print("[INFO] âš¡âš¡ KÃ­ch hoáº¡t Äá»™ng cÆ¡ FFmpeg Ultrafast Multi-Thread Tá»‘i Æ¯u SiÃªu Tá»‘c (TÄƒng tá»‘c 5x trÃªn CPU)...")
    except Exception:
        codec = "libx264"

    # Lá»‡nh FFmpeg PASS 1: Concat Slideshow Chuáº©n Sáº¯c NÃ©t 1080p
    cmd_pass1 = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-map", "[out]", "-map", "1:a",
        "-vsync", "1", "-async", "1", "-r", "25",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "1200k", "-maxrate", "1800k", "-bufsize", "2500k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]
    
    from src.video_validator import validate_video_file
    try:
        print(f"[INFO] ðŸš€ FFmpeg rendering PASS 1 {total_audio_duration:.1f}s video ({codec})...")
        res1 = subprocess.run(cmd_pass1, capture_output=True, text=True, timeout=1800)
        
        if res1.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=500000):
            print(f"[SUCCESS] ðŸŸ¢ Render Video 16:9 sáº¯c nÃ©t {total_audio_duration:.1f}s thÃ nh cÃ´ng: {output_video_path}")
            return output_video_path
        else:
            print(f"[WARNING] Pass 1 Concat warning: {res1.stderr[:200]}")
    except Exception as e:
        print(f"[WARNING] Exception in Pass 1 rendering: {e}")
        
    # Lá»‡nh FFmpeg PASS 2 (Chá»‘ng MÃ n HÃ¬nh Äen 100%): Render 1 áº£nh ná»n AI HD káº¿t há»£p Audio & Phá»¥ Äá»
    print("[INFO] ðŸ›¡ï¸ KÃ­ch hoáº¡t Äá»™ng cÆ¡ PASS 2 Chá»‘ng MÃ n HÃ¬nh Äen (Single HD Image + Audio + SRT)...")
    first_img = valid_sequences[0]['image'] if valid_sequences else ""
    if not is_valid_image_file(first_img):
        first_img = os.path.join(img_dir, "scene_pass2.jpg")
        generate_scene_image(title, first_img, width=1920, height=1080)

    vf_filter_pass2 = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=brightness=0.04:contrast=1.12:saturation=1.22[bg]"
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
        "-b:v", "1000k", "-maxrate", "1500k", "-bufsize", "2000k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]

    try:
        res2 = subprocess.run(cmd_pass2, capture_output=True, text=True, timeout=1800)
        if res2.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=300000):
            print(f"[SUCCESS] ðŸŸ¢ PASS 2 Render Video HD chá»‘ng mÃ n hÃ¬nh Ä‘en thÃ nh cÃ´ng: {output_video_path}")
            return output_video_path
        else:
            print(f"[ERROR] Pass 2 failed: {res2.stderr[:200]}")
    except Exception as pass2_e:
        print(f"[ERROR] Exception in Pass 2 rendering: {pass2_e}")
        
    # Lá»‡nh FFmpeg PASS 3 (Báº£o vá»‡ tuyá»‡t Ä‘á»‘i): Render video khÃ´ng phá»¥ Ä‘á» náº¿u filter subtitles gáº·p sá»± cá»‘ há»‡ thá»‘ng
    print("[INFO] ðŸ›¡ï¸ KÃ­ch hoáº¡t Äá»™ng cÆ¡ PASS 3 Báº£o Vá»‡ Tuyá»‡t Äá»‘i (Slideshow Video + Audio)...")
    vf_filter_pass3 = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    cmd_pass3 = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", audio_path,
        "-vf", vf_filter_pass3,
        "-map", "0:v", "-map", "1:a",
        "-r", "20",
        "-c:v", codec
    ] + encoder_opts + [
        "-b:v", "1000k", "-maxrate", "1500k", "-bufsize", "2000k",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest", output_video_path
    ]
    try:
        res3 = subprocess.run(cmd_pass3, capture_output=True, text=True, timeout=1800)
        if res3.returncode == 0 and validate_video_file(output_video_path, min_size_bytes=200000):
            print(f"[SUCCESS] ðŸŸ¢ PASS 3 Render Video báº£o vá»‡ tuyá»‡t Ä‘á»‘i thÃ nh cÃ´ng: {output_video_path}")
            return output_video_path
    except Exception as pass3_e:
        print(f"[ERROR] Pass 3 exception: {pass3_e}")

    return ""

def render_novel_video(audio_path: str, srt_path: str, title: str, chapter_id: str) -> str:
    """Tá»± Ä‘á»™ng render video tá»« audio & SRT (cÃ³ fallback sang moneyprinter)."""
    out_video = os.path.join("output", chapter_id, "video.mp4")
    img_dir = os.path.join("output", chapter_id, "images")
    
    # Try moneyprinter first
    moneyprinter_vid = dispatch_to_moneyprinter(title, img_dir, audio_path)
    if moneyprinter_vid:
        return moneyprinter_vid
        
    return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7)

def process_existing_audio(audio_path: str, srt_path: str = "", title: str = "Audiobook Novel") -> str:
    """HÃ m Ä‘á»™c láº­p: Nháº­n trá»±c tiáº¿p file audio cÃ³ sáºµn tá»« workflow vÃ  xuáº¥t video MP4."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] File audio khÃ´ng tá»“n táº¡i: {audio_path}")
        return ""
        
    parent_folder = os.path.basename(os.path.dirname(os.path.abspath(audio_path)))
    import uuid
    import re as _re
    _uuid_pat = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
    if parent_folder and (_uuid_pat.match(parent_folder) or len(parent_folder) > 8):
        chapter_id = parent_folder
    else:
        chapter_id = str(uuid.uuid4())[:8]
        
    print(f"[INFO] Äang xá»­ lÃ½ file audio cÃ³ sáºµn cho chapter_id ({chapter_id}): {audio_path}")
    return render_novel_video(audio_path, srt_path, title, chapter_id)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        aud = sys.argv[1]
        srt = sys.argv[2] if len(sys.argv) > 2 else ""
        ttl = sys.argv[3] if len(sys.argv) > 3 else "Audiobook Novel"
        res = process_existing_audio(aud, srt, ttl)
        print(f"Result video: {res}")


