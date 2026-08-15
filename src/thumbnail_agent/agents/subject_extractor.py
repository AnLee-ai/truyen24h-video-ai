class SubjectExtractor:
    """Agent 4: Nhận diện khuôn mặt (OpenCV + YOLO-Face & Sharpness Filter)"""
    def __init__(self):
        pass
        
    def extract_subject_info(self, image_path: str) -> dict:
        """Tính điểm độ nét (Laplacian) và trả về Bounding Box (x,y,w,h) của khuôn mặt."""
        print(f"[SubjectExtractor] Phân tích khuôn mặt trên ảnh {image_path}...")
        # Mock logic
        return {
            "sharpness_score": 85.5,
            "face_bounding_box": {"x": 200, "y": 150, "w": 100, "h": 120}
        }
