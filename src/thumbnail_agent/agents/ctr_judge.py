from src.thumbnail_agent.models import ScoreBreakdown

class CtrJudge:
    """Agent 9: Multi-Criteria Vision LLM Judge v2.0"""
    def __init__(self):
        pass
        
    def evaluate_thumbnail(self, image_path: str, saliency_score: float) -> ScoreBreakdown:
        """Sử dụng Gemini Vision kết hợp Saliency Score để chấm 7 tiêu chí CTR."""
        print(f"[CtrJudge] Đánh giá toàn diện Thumbnail {image_path}...")
        # Mock logic
        return ScoreBreakdown(
            relevance=8.5,
            impact=9.0,
            character_quality=8.0,
            readability=9.5,
            composition=(saliency_score / 10.0),
            curiosity=8.5,
            mobile_visibility=9.0,
            trustworthiness=10.0
        )
