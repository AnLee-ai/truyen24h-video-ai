from src.thumbnail_agent.models import ScoreBreakdown
from src.thumbnail_agent.pipeline import run_thumbnail_pipeline

def test_score_breakdown_calculation():
    score = ScoreBreakdown(
        relevance=10.0,
        impact=10.0,
        character_quality=10.0,
        readability=10.0,
        composition=10.0,
        curiosity=10.0,
        mobile_visibility=10.0,
        trustworthiness=10.0
    )
    assert score.total_score == 10.0

def test_thumbnail_pipeline_mock():
    # Since the pipeline currently uses mock prints and returns a dictionary, 
    # we just want to ensure it executes without raising exceptions and returns expected schema.
    res = run_thumbnail_pipeline("mock_video.mp4", "Chương 1")
    
    assert "top_variants" in res
    assert isinstance(res["top_variants"], list)
    assert len(res["top_variants"]) > 0
    
    variant = res["top_variants"][0]
    assert "ctr_score" in variant
    assert "concept" in variant
    assert "is_selected" in variant
