
class StoryAnalyst:
    """Agent 2: Phân tích cốt truyện (Whisper + Gemini VLM Hook Extractor)"""
    def __init__(self):
        pass
        
    def extract_hooks(self, text_transcript: str) -> list[str]:
        """Sử dụng Gemini VLM / Prompt NLP để trích xuất 2-5 từ hook mạnh mẽ."""
        print("[StoryAnalyst] Đang phân tích thoại và trích xuất câu Hook...")
        # Mock logic
        return ["Sức mạnh khủng khiếp!", "Bá chủ trùng sinh", "Đỉnh cao tu tiên"]
