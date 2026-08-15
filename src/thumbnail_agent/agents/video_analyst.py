import os

class VideoAnalyst:
    """Agent 1: Phân tích video (Cắt cảnh & Trích xuất keyframe)"""
    def __init__(self):
        pass
        
    def extract_keyframes(self, video_path: str, output_dir: str = "output/keyframes") -> list[str]:
        """Dùng PySceneDetect và FFmpeg để cắt keyframes từ video."""
        print(f"[VideoAnalyst] Đang trích xuất keyframe từ {video_path}...")
        os.makedirs(output_dir, exist_ok=True)
        # Mock logic
        return [f"{output_dir}/frame_1.jpg", f"{output_dir}/frame_2.jpg"]
