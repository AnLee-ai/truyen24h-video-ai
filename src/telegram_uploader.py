import os
import requests
from src import config

def generate_seo_caption(chapter_num: int, chapter_title: str) -> str:
    """Generate SEO-optimized caption with hashtags and chapter summary formatting."""
    hashtags = "#VạnCổThầnVương #TiêuViêm #VânVận #ReviewTruyện #Webtoon2D #PhimHoạtHình #TiênHiệp #HuyềnHuyễn"
    return (
        f"🎙️ *Truyện 24h Audio - Tập {chapter_num}*\n\n"
        f"📖 *Chương {chapter_num}: {chapter_title}*\n\n"
        f"🔥 Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, nén ép vạn giới thần ma!\n"
        f"✨ Tác phẩm sản xuất tự động bằng AI 4K, kịch bản kịch tính & video 16:9 sắc nét.\n\n"
        f"🏷️ {hashtags}"
    )

def send_progress_status_to_telegram(status_text: str) -> bool:
    """Send a quick progress status update text message to Telegram channel."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        data = {
            'chat_id': config.TELEGRAM_CHAT_ID,
            'text': status_text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=data, timeout=15)
        return response.status_code == 200
    except Exception:
        return False

def send_audio_to_telegram(audio_path: str, caption: str, title: str | None = None, srt_path: str | None = None) -> bool:
    """
    Sends an audio file (and optional subtitle file) to a Telegram channel/chat.
    
    Args:
        audio_path (str): Local path to the MP3/WAV file.
        caption (str): Caption text to accompany the audio.
        title (str): Title tag for the audio file.
        srt_path (str): Optional path to the subtitle SRT file.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[WARNING] Telegram credentials are not configured. Skipping upload.")
        return False
        
    if not os.path.exists(audio_path):
        print(f"[ERROR] Audio file does not exist: {audio_path}")
        return False
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendAudio"
    
    print(f"[INFO] Uploading audio to Telegram chat/channel: {config.TELEGRAM_CHAT_ID}...")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            files = {
                'audio': (os.path.basename(audio_path), audio_file, 'audio/mpeg')
            }
            data = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown',
                'performer': 'Truyện 24h Audio'
            }
            if title:
                data['title'] = title
                
            response = requests.post(url, data=data, files=files, timeout=300)
            if response.status_code != 200 and "can't parse entities" in response.text:
                # Fallback to plain text caption if markdown format fails
                data.pop('parse_mode', None)
                response = requests.post(url, data=data, files=files, timeout=300)
            
        if response.status_code == 200:
            print("[INFO] Audio uploaded successfully to Telegram.")
            
            # If SRT subtitle is provided, send it as a document next with human-readable filename
            if srt_path and os.path.exists(srt_path):
                print(f"[INFO] Uploading subtitle SRT: {srt_path}...")
                srt_name = f"{title or 'Subtitle'}.srt"
                send_document_to_telegram(srt_path, f"Phụ đề chương: {title or 'SRT'}", custom_filename=srt_name)
            
            return True
        else:
            print(f"[ERROR] Telegram upload failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error during Telegram upload: {e}")
        return False

def send_photo_to_telegram(photo_path: str, caption: str) -> bool:
    """Send a photo (like 16:9 YouTube Thumbnail) to the Telegram channel."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[WARNING] Telegram credentials are not configured. Skipping photo upload.")
        return False
        
    if not os.path.exists(photo_path):
        print(f"[ERROR] Photo file does not exist: {photo_path}")
        return False
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    print(f"[INFO] Uploading 16:9 Thumbnail Photo to Telegram chat/channel: {config.TELEGRAM_CHAT_ID}...")
    
    try:
        with open(photo_path, 'rb') as photo_file:
            files = {
                'photo': (os.path.basename(photo_path), photo_file, 'image/jpeg')
            }
            data = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, files=files, timeout=60)
            if response.status_code != 200 and "can't parse entities" in response.text:
                data.pop('parse_mode', None)
                response = requests.post(url, data=data, files=files, timeout=60)
                
            if response.status_code == 200:
                print("[SUCCESS] 🖼️ 16:9 Thumbnail photo uploaded successfully to Telegram!")
                return True
            else:
                print(f"[ERROR] Telegram photo upload failed ({response.status_code}): {response.text}")
                return False
    except Exception as e:
        print(f"[ERROR] Error uploading photo to Telegram: {e}")
        return False

def send_document_to_telegram(doc_path: str, caption: str, custom_filename: str = None) -> bool:
    """Send any document (like SRT file) to the Telegram channel."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendDocument"
    filename = custom_filename or os.path.basename(doc_path)
    try:
        with open(doc_path, 'rb') as doc_file:
            files = {
                'document': (filename, doc_file, 'application/octet-stream')
            }
            data = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, files=files, timeout=60)
            
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Subtitle upload failed: {e}")
        return False

def send_video_to_telegram(video_path: str, caption: str, public_url: str = "") -> bool:
    """Send a video MP4 file to Telegram channel using sendVideo API, with automatic fast compression if file exceeds Telegram 50MB limit."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[WARNING] Telegram credentials not configured for video upload.")
        return False
        
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file does not exist: {video_path}")
        return False
        
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"[INFO] Initial Video MP4 Size: {file_size_mb:.2f} MB")
    
    target_upload_path = video_path
    
    # Nếu file > 48MB (vượt giới hạn 50MB của Telegram Bot API), nén siêu tốc bằng FFmpeg xuống <45MB
    if file_size_mb > 48.0:
        compressed_path = video_path.replace(".mp4", "_tg_compressed.mp4")
        print(f"[INFO] Video ({file_size_mb:.2f}MB) vượt giới hạn 50MB Telegram. Đang tự động nén mượt xuống <45MB...")
        import subprocess
        try:
            # Bitrate 600k giữ độ phân giải 1080p sắc nét và kích thước file chuẩn Telegram
            cmd_comp = [
                "ffmpeg", "-y", "-i", video_path,
                "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "650k", "-maxrate", "900k", "-bufsize", "1500k",
                "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                compressed_path
            ]
            comp_res = subprocess.run(cmd_comp, capture_output=True, text=True, timeout=300)
            if comp_res.returncode == 0 and os.path.exists(compressed_path) and os.path.getsize(compressed_path) > 1000:
                target_upload_path = compressed_path
                new_size = os.path.getsize(target_upload_path) / (1024 * 1024)
                print(f"[SUCCESS] Đã nén video Telegram thành công: {new_size:.2f} MB")
        except Exception as e:
            print(f"[WARNING] Auto compression error: {e}")

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo"
    curr_size = os.path.getsize(target_upload_path) / (1024 * 1024)
    print(f"[INFO] Uploading Video MP4 ({curr_size:.1f}MB) to Telegram channel: {config.TELEGRAM_CHAT_ID}...")
    
    try:
        with open(target_upload_path, 'rb') as video_file:
            files = {
                'video': (os.path.basename(target_upload_path), video_file, 'video/mp4')
            }
            data = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, files=files, timeout=600)
            if response.status_code != 200 and "can't parse entities" in response.text:
                data.pop('parse_mode', None)
                response = requests.post(url, data=data, files=files, timeout=600)
                
            if response.status_code == 200:
                print("[SUCCESS] Video MP4 uploaded successfully to Telegram!")
                return True
            else:
                print(f"[ERROR] Telegram video upload failed ({response.status_code}): {response.text}")
                if public_url:
                    # Gửi tin nhắn thông báo link nếu upload file thất bại
                    msg_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
                    requests.post(msg_url, data={'chat_id': config.TELEGRAM_CHAT_ID, 'text': f"{caption}\n\n🔗 Xem Video HD: {public_url}"})
                return False
    except Exception as e:
        print(f"[ERROR] Error uploading video to Telegram: {e}")
        return False
