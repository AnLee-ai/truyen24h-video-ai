import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ScoreBreakdown(BaseModel):
    relevance: float = Field(0.0, description="Khớp nội dung video (20%)")
    impact: float = Field(0.0, description="Độ tương phản và tác động thị giác (20%)")
    character_quality: float = Field(0.0, description="Chất lượng và thần thái nhân vật (15%)")
    readability: float = Field(0.0, description="Khả năng đọc chữ trên mobile (15%)")
    composition: float = Field(0.0, description="Bố cục và Saliency Match (10%)")
    curiosity: float = Field(0.0, description="Kích thích tò mò (10%)")
    mobile_visibility: float = Field(0.0, description="Khả năng hiển thị mobile (5%)")
    trustworthiness: float = Field(0.0, description="An toàn chính sách (5%)")
    
    @property
    def total_score(self) -> float:
        return (
            0.20 * self.relevance +
            0.20 * self.impact +
            0.15 * self.character_quality +
            0.15 * self.readability +
            0.10 * self.composition +
            0.10 * self.curiosity +
            0.05 * self.mobile_visibility +
            0.05 * self.trustworthiness
        )

class ThumbnailConcept(BaseModel):
    concept_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    visual_description: str
    hook_text: str
    mood: str

class ThumbnailVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    concept: ThumbnailConcept
    image_url: Optional[str] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    ctr_score: float = 0.0
    is_selected: bool = False

class ThumbnailJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    video_path: str
    chapter_title: str
    status: str = "processing"
    concepts: List[ThumbnailConcept] = []
    variants: List[ThumbnailVariant] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
