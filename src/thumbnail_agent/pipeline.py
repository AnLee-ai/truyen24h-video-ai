from src.thumbnail_agent.agents.video_analyst import VideoAnalyst
from src.thumbnail_agent.agents.story_analyst import StoryAnalyst
from src.thumbnail_agent.agents.competitor_benchmark import CompetitorBenchmark
from src.thumbnail_agent.agents.subject_extractor import SubjectExtractor
from src.thumbnail_agent.agents.art_director import ArtDirector
from src.thumbnail_agent.agents.layered_generator import LayeredGenerator
from src.thumbnail_agent.agents.layout_engine import LayoutEngine
from src.thumbnail_agent.agents.saliency_judge import SaliencyJudge
from src.thumbnail_agent.agents.ctr_judge import CtrJudge
from src.thumbnail_agent.models import ThumbnailVariant

def run_thumbnail_pipeline(video_path: str, chapter_title: str) -> dict:
    """Điều phối luồng 9 Agent tạo Thumbnail."""
    print(f"[Pipeline] Khởi động 9-Agent Thumbnail Engine cho: {chapter_title}")
    
    # Init Agents
    agent_vid = VideoAnalyst()
    agent_story = StoryAnalyst()
    agent_comp = CompetitorBenchmark()
    agent_sub = SubjectExtractor()
    agent_art = ArtDirector()
    agent_gen = LayeredGenerator()
    agent_lay = LayoutEngine()
    agent_sal = SaliencyJudge()
    agent_ctr = CtrJudge()
    
    # 1. Understand Video & Story
    keyframes = agent_vid.extract_keyframes(video_path)
    hooks = agent_story.extract_hooks("Nội dung mô phỏng chương truyện")
    
    # 2. Competitor Benchmark
    comp_data = agent_comp.analyze_competition(chapter_title)
    
    # 3. Subject & Concepts
    sub_data = agent_sub.extract_subject_info(keyframes[0] if keyframes else "mock.jpg")
    concepts = agent_art.synthesize_concepts(hooks, comp_data)
    
    variants = []
    # 4. Generate & Composite
    for idx, concept in enumerate(concepts):
        layers = agent_gen.generate_layers(concept.visual_description)
        out_path = f"output/thumb_var_{idx}.jpg"
        final_img = agent_lay.composite_thumbnail(layers, concept.hook_text, sub_data["face_bounding_box"], out_path)
        
        # 5. Judge
        saliency = agent_sal.simulate_eye_tracking(final_img, [{"type": "text"}, {"type": "face"}])
        score = agent_ctr.evaluate_thumbnail(final_img, saliency)
        
        variant = ThumbnailVariant(
            job_id="mock-job",
            concept=concept,
            image_url=final_img,
            score_breakdown=score,
            ctr_score=score.total_score
        )
        variants.append(variant)
        
    # Xếp hạng
    variants.sort(key=lambda x: x.ctr_score, reverse=True)
    if variants:
        variants[0].is_selected = True
        print(f"[Pipeline] Hoàn tất! Best Thumbnail: {variants[0].image_url} (Score: {variants[0].ctr_score:.2f})")
        
    return {"top_variants": [v.model_dump() for v in variants]}
