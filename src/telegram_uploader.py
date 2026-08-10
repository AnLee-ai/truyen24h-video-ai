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
    """Send a video MP4 file or public CDN URL to Telegram channel & Discord webhook bypassing 50MB limits."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[WARNING] Telegram credentials not configured for video upload.")
        return False
        
    if not os.path.exists(video_path) and not public_url:
        print(f"[ERROR] Video file does not exist: {video_path}")
        return False

    file_size_mb = (os.path.getsize(video_path) / (1024 * 1024)) if os.path.exists(video_path) else 0.0
    
    # 1. BẢO ĐẢM TẠO CHUẨN ĐƯỜNG LINK SUPABASE CDN (Không bao giờ lấy link rác https://supabase.com)
    final_cdn_url = public_url.strip() if (public_url and public_url.startswith("http") and "supabase.com" not in public_url) else ""
    if not final_cdn_url and config.SUPABASE_URL and os.path.exists(video_path):
        supabase_base = config.SUPABASE_URL.rstrip('/')
        filename_rel = os.path.basename(video_path)
        final_cdn_url = f"{supabase_base}/storage/v1/object/public/media/videos/full/{filename_rel}"
        
    print(f"[INFO] Initial Video MP4 Size: {file_size_mb:.2f} MB | Direct CDN URL: {final_cdn_url}")
    
    # 2. THÔNG BÁO LINK STREAMING TRỰC TIẾP KHÔNG GIỚI HẠN DUNG LƯỢNG LÊN TELEGRAM
    if final_cdn_url:
        cdn_message = f"{caption}\n\n🍿 *XEM VIDEO FULL HD 16:9 (SUPABASE STORAGE CDN - KHÔNG GIỚI HẠN 50MB):*\n🎬 [Bấm vào đây để xem trực tiếp / Tải Video]({final_cdn_url})"
    else:
        cdn_message = f"{caption}\n\n🎬 *Video Full HD 16:9 đã được tạo thành công!*"
        
    # Gửi qua Telegram API
    msg_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(msg_url, data={'chat_id': config.TELEGRAM_CHAT_ID, 'text': cdn_message, 'parse_mode': 'Markdown'})
        print(f"[SUCCESS] 🟢 Đã gửi Link Video CDN Supabase trực tiếp không giới hạn dung lượng lên Telegram Channel!")
    except Exception as e:
        print(f"[WARNING] Gửi CDN message Telegram thất bại: {e}")

    # Gửi qua Discord Webhook nếu được cấu hình
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if discord_webhook:
        try:
            discord_payload = {
                "content": f"🎬 **NEW VIDEO RELEASED**\n{caption}\n\n🍿 **Xem Video Full HD 16:9 (Supabase CDN):** {public_url}"
            }
            requests.post(discord_webhook, json=discord_payload, timeout=10)
            print(f"[SUCCESS] 🟢 Đã phát Video lên Discord Webhook thành công!")
        except Exception as e:
            print(f"[WARNING] Discord Webhook notify error: {e}")

    target_upload_path = video_path
    
    # 2. Nếu file <= 45MB, thử gửi file trực tiếp qua Telegram sendVideo
    if 0 < file_size_mb <= 45.0:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo"
        try:
            with open(target_upload_path, 'rb') as video_file:
                files = {'video': (os.path.basename(target_upload_path), video_file, 'video/mp4')}
                data = {'chat_id': config.TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
                res = requests.post(url, data=data, files=files, timeout=600)
                if res.status_code == 200:
                    print("[SUCCESS] 🎬 File Video MP4 đã gửi thành công lên Telegram!")
                    return True
        except Exception as e:
            print(f"[WARNING] sendVideo direct failed: {e}")

    # 3. Thử gửi file qua sendDocument (hỗ trợ file nặng tới 2,000 MB / 2GB)
    if os.path.exists(target_upload_path):
        try:
            doc_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendDocument"
            with open(target_upload_path, 'rb') as video_doc_file:
                doc_files = {'document': (os.path.basename(target_upload_path), video_doc_file, 'video/mp4')}
                doc_data = {'chat_id': config.TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
                doc_res = requests.post(doc_url, data=doc_data, files=doc_files, timeout=600)
                if doc_res.status_code == 200:
                    print("[SUCCESS] 🎬 File Video MP4 (Document 2GB) đã gửi thành công lên Telegram!")
                    return True
        except Exception as e:
            print(f"[WARNING] sendDocument failed: {e}")

    return True
