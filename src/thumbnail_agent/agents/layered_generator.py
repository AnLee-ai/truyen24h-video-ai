class LayeredGenerator:
    """Agent 6: Diffusers/Imagen + RemBG Cutout"""
    def __init__(self):
        pass
        
    def generate_layers(self, concept_prompt: str) -> dict:
        """Sinh ảnh gốc và tách lớp (BG, Subject, VFX) bằng RemBG."""
        print(f"[LayeredGenerator] Sinh và tách lớp cho prompt: {concept_prompt[:30]}...")
        # Mock logic
        return {
            "bg_layer": "output/layers/bg.png",
            "subject_layer": "output/layers/subject.png",
            "vfx_layer": "output/layers/vfx.png"
        }
