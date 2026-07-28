import json
from src.writer import call_gemini

def generate_seo_metadata(title: str, chapter_number: int, content_snippet: str) -> dict:
    """Feature 4 & Feature 10: Tự động tạo SEO Metadata, Tags, Hashtags và Tóm Tắt Chương lôi cuốn cho YouTube/TikTok/Telegram."""
    prompt = f"""
    Bạn là chuyên gia SEO YouTube và TikTok Content Creator. Hãy phân tích chương tiểu thuyết sau và tạo bộ Metadata thu hút triệu view:
    Tiêu đề: {title}
    Chương: {chapter_number}
    Nội dung ngắn: {content_snippet[:1000]}
    
    Hãy xuất ra định dạng JSON:
    {{
      "youtube_title": "Tiêu đề YouTube gây tò mò kích thích click",
      "summary": "Tóm tắt hấp dẫn 2-3 câu ngắn gọn",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
      "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
      "engagement_question": "Câu hỏi bình luận tương tác cho khán giả"
    }}
    """
    try:
        res = call_gemini(prompt, json_mode=True)
        from src.writer import safe_loads
        return safe_loads(res)
    except Exception as e:
        print(f"[WARNING] SEO metadata generation fallback: {e}")
        return {
            "youtube_title": f"Chương {chapter_number}: {title} | Truyện Audio Hay Nhất",
            "summary": f"Diễn biến cực kỳ kịch tính trong Chương {chapter_number}: {title}.",
            "tags": ["truyen audio", "tieu thuyet ai", "truyen24h", f"chuong {chapter_number}"],
            "hashtags": ["#TruyenAudio", "#TieuThuyet", "#Truyen24h"],
            "engagement_question": "Bạn nghĩ nhân vật chính nên làm gì ở tập tiếp theo? Hãy để lại bình luận nhé!"
        }
