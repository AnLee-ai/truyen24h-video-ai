from src.thumbnail_agent.models import ThumbnailConcept

class ArtDirector:
    """Agent 5: Gemini Concept Synthesizer"""
    def __init__(self):
        pass
        
    def synthesize_concepts(self, story_hooks: list[str], competitor_data: dict) -> list[ThumbnailConcept]:
        """Tổng hợp dữ liệu để sinh ra các concept Thumbnail đột phá."""
        print("[ArtDirector] Đang sáng tạo concept Thumbnail...")
        # Mock logic
        return [
            ThumbnailConcept(title="Cận cảnh anh hùng", visual_description="Chân dung góc hẹp, ánh sáng tương phản", hook_text=story_hooks[0], mood="Căng thẳng"),
            ThumbnailConcept(title="Khoảnh khắc bùng nổ", visual_description="Kỹ năng tung ra, hiệu ứng ánh sáng rực rỡ", hook_text="Vô Địch!", mood="Hào hùng")
        ]
