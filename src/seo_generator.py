from src.writer import call_gemini, safe_loads

def generate_seo_metadata(title: str, chapter_number: int, content_snippet: str) -> dict:
    """Tự động tạo SEO Metadata, Tags, Hashtags và Tiêu đề Hook triệu view mang thương hiệu chính thức Truyện 24h."""
    prompt = f"""
    Bạn là chuyên gia Content Creator đứng sau kênh YouTube 'Truyện 24h'. Hãy phân tích chương tiểu thuyết sau và viết bộ SEO Metadata cực kỳ thu hút:
    Tiêu đề: {title}
    Chương: {chapter_number}
    Trích đoạn nội dung: {content_snippet[:1000]}
    
    Yêu cầu tiêu đề YouTube mang thương hiệu 'Truyện 24h':
    - Bắt đầu bằng 1 câu Hook kịch tính gây tò mò cao (ví dụ: 'Bị Khinh Nhược Vô Năng, Thức Tỉnh Hệ Thống Bá Chủ', 'Luyện Thành Ma Công Cổ Đại, Đập Tan Học Viện').
    - Kết thúc bằng: '- Tập {chapter_number}: {title} | Truyện 24h'
    
    Hãy xuất ra định dạng JSON:
    {{
      "youtube_title": "[Câu Hook Giật Gân] - Tập {chapter_number}: {title} | Truyện 24h",
      "summary": "Tóm tắt kịch tính 2-3 câu ngắn gọn cuốn hút",
      "tags": ["truyen 24h", "truyen 24h audio", "review truyen hay", "truyen manhwa audio", "tap {chapter_number}"],
      "hashtags": ["#Truyen24h", "#Truyen24hAudio", "#ReviewTruyenHay"],
      "engagement_question": "Anh em nghĩ nhân vật chính nên dùng chiêu gì ở tập tới? Đội nào ủng hộ thì comment bên dưới cùng Truyện 24h nhé!"
    }}
    """
    try:
        res = call_gemini(prompt, json_mode=True)
        return safe_loads(res)
    except Exception as e:
        print(f"[WARNING] SEO metadata generation fallback: {e}")
        return {
            "youtube_title": f"Bị Phế Võ Công, Thức Tỉnh Sức Mạnh Bá Chủ - Tập {chapter_number}: {title} | Truyện 24h",
            "summary": f"Diễn biến cực kỳ kịch tính và gay cấn trong Tập {chapter_number}: {title}.",
            "tags": ["truyen 24h", "truyen 24h audio", "review truyen hay", "truyen manhwa audio", f"tap {chapter_number}"],
            "hashtags": ["#Truyen24h", "#Truyen24hAudio", "#ReviewTruyenHay"],
            "engagement_question": "Anh em nghĩ nhân vật chính nên xử lý kẻ thù thế nào ở tập tiếp theo? Để lại bình luận bên dưới cùng Truyện 24h nhé!"
        }
