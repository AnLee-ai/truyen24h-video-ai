import os
import subprocess

def validate_video_file(video_path: str, min_size_bytes: int = 100000) -> bool:
    """Feature 8: Tự động kiểm tra chất lượng video MP4 đã render (kích thước, độ dài, tính toàn vẹn)."""
    if not video_path or not os.path.exists(video_path):
        print(f"[VALIDATION FAIL] Video file does not exist: {video_path}")
        return False
        
    size = os.path.getsize(video_path)
    if size < min_size_bytes:
        print(f"[VALIDATION FAIL] Video file size too small: {size} bytes")
        return False
        
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            duration = float(res.stdout.strip())
            if duration > 1.0:
                print(f"[VALIDATION PASSED] Video is valid! Duration: {duration:.2f}s ({duration/60:.2f}m), Size: {size/1024/1024:.2f}MB")
                return True
            else:
                print(f"[VALIDATION FAIL] Video duration too short: {duration}s")
                return False
        else:
            print("[VALIDATION FAIL] Corrupted MP4 stream or header error detected by ffprobe.")
            return False
    except subprocess.TimeoutExpired:
        print(f"[VALIDATION FAIL] ffprobe timed out probing {video_path}. File may be corrupted or locked.")
        return False
    except Exception:
        print("[VALIDATION WARNING] Could not run ffprobe. Falling back to size validation.")
        return size > 5000000
