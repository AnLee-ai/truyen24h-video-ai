import os
import requests
from src import config

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
            
        if response.status_code == 200:
            print("[INFO] Audio uploaded successfully to Telegram.")
            
            # If SRT subtitle is provided, send it as a document next
            if srt_path and os.path.exists(srt_path):
                print(f"[INFO] Uploading subtitle SRT: {srt_path}...")
                send_document_to_telegram(srt_path, f"Phụ đề chương: {title or 'SRT'}")
            
            return True
        else:
            print(f"[ERROR] Telegram upload failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error during Telegram upload: {e}")
        return False

def send_document_to_telegram(doc_path: str, caption: str) -> bool:
    """Send any document (like SRT file) to the Telegram channel."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(doc_path, 'rb') as doc_file:
            files = {
                'document': (os.path.basename(doc_path), doc_file, 'application/octet-stream')
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
