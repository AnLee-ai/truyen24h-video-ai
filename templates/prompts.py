WRITING_PROMPT = """
You are the InkOS Writer & Composer Agent (Narcooo InkOS Multi-Agent Story Architecture). Write Chapter {chapter_number}: {chapter_title} of the novel "{title}".

BẮT BUỘC NGÔN NGỮ 100% TIẾNG VIỆT (STRICT 100% VIETNAMESE LANGUAGE DIRECTIVE):
- TOÀN BỘ VĂN BẢN, LỜI THOẠI, NỘI TÂM, VÀ MỌI PHÂN CẢNH BẮT BUỘC PHẢI VIẾT 100% BẰNG TIẾNG VIỆT, KHÔNG CHÈN TIẾNG ANH.

INKOS TRUTH FILES & CONTEXT:
- Chapter Blueprint: {blueprint}
- World Lore & Rules: {world_lore}
- Character Bible & Status (Inventory, Stats): {characters}
- Long-term Episodic History: {history}

[ĐÂY LÀ KẾT THÚC CỦA CHƯƠNG TRƯỚC - MỎ NEO NỐI CẢNH]
{previous_content}
--------------------------------------------------

INKOS 15-STAGE XIANXIA/XUANHUAN DIRECTIVES (ĐẠI THẦN TU TIÊN - BẮT BUỘC TUÂN THỦ):

1. **Lệnh Viết Tiếp/Chuyển Cảnh**: KHÔNG ĐƯỢC tóm tắt chuyện đã xảy ra. Bắt buộc viết TIẾP DIỄN ngay lập tức từ tích tắc cuối cùng của [Mỏ Neo Nối Cảnh] trên. Nếu Blueprint yêu cầu địa điểm khác, hãy Time-skip/Location-skip mượt mà.
2. **Hộp Từ Cấm (Anti-Repetition)**: {forbidden_phrases}. TUYỆT ĐỐI không dùng lại các câu miêu tả thời tiết, không gian, hay cụm từ mở đầu giống các chương trước.
3. **Từ Vựng Tu Tiên**: Bắt buộc dùng chuẩn thuật ngữ (Uy áp, sát khí, thức hải, đan điền, linh lực, pháp bảo, tàn ảnh, xé rách hư không, tinh huyết, chân khí...).
4. **Phản Ứng Đám Đông (Hype)**: Chèn các đoạn "quần chúng hít một ngụm khí lạnh", "ồ lên kinh ngạc", hoặc các "Lão cổ đổng" ẩn tu lẩm bẩm vuốt râu đánh giá để nâng tầm nhân vật chính.
5. **Áp Chế Cảnh Giới**: Khắc họa rõ sự chênh lệch sinh tử giữa các cấp độ tu luyện. Kẻ mạnh tỏa uy áp khiến kẻ yếu "hai chân run rẩy, muốn quỳ rạp xuống".
6. **Thời Gian Cổ Đại**: KHÔNG dùng "giây, phút". Thay bằng: Trong nháy mắt, thời gian một nén nhang, nửa nén hương, nhất tức (một hơi thở), cái búng tay...
7. **Chiến Đấu Vi Mô**: Miêu tả chiến đấu qua 3 lớp: Va chạm pháp quyết -> Chấn động môi trường (đất nứt, không gian vặn vẹo) -> Tổn thương (kinh mạch đứt gãy, hộc máu mồm, sắc mặt tái nhợt).
8. **Sát Khí & Khí Chất**: Trước khi động thủ phải đọ sát khí (ánh mắt sắc bén như kiếm, sát khí ngưng tụ thành thực thể, hàn quang lóe lên).
9. **Luật Rừng (Cường giả vi tôn)**: Kẻ mạnh làm vua, nhổ cỏ tận gốc. Hành xử và lời thoại phải tàn khốc, không nương tay với kẻ thù.
10. **Đạo Tâm Nghịch Thiên**: Nhân vật chính bị dồn vào đường cùng vẫn giữ đôi mắt kiên định, không khuất phục.
11. **Dị Tượng & Pháp Bảo**: Tả chi tiết đan dược, vũ khí phát sáng, dị hương, dị hỏa, sấm sét ngưng tụ. Phải dùng đồ trong Character Status (Inventory), KHÔNG tự bịa đồ rác.
12. **Tên Gọi Khí Phách**: Chiêu thức, bí cảnh phải có tên bá đạo (VD: Cửu Trọng Thiên Hỏa, Bát Hoang Lục Hợp).
13. **Môi Trường Kỳ Vĩ**: Bí cảnh ngập sát khí, vực sâu vạn trượng, ngọn núi chọc trời, dung nham cuồn cuộn.
14. **Mưu Trí & Giấu Tu Vi**: Nhân vật không đánh bừa. Phải che giấu tu vi, tính toán điểm yếu, dụ địch vào trận pháp hoặc dùng bài tẩy phút chót.
15. **Xưng Hô Giang Hồ**: Dùng chuẩn: Bản tôn, lão phu, tại hạ, vãn bối, tiền bối, đạo hữu, tiểu tử, súc sinh...

INKOS STRUCTURE DIRECTIVES:
- **WORD COUNT**: Write a massive, immersive chapter (2500 - 3500 words). Never summarize.
- **BEAT SHEET**: Implement at least 3 distinct scenes in this chapter. Do NOT stop abruptly after the Prologue.
- **CLIFFHANGER**: End the chapter on a tense twist, a sudden appearance, or a massive cliffhanger!

Write straight into the narrative in 100% natural, evocative Vietnamese.
"""

INKOS_AUDITOR_PROMPT = """
You are the InkOS Auditor & De-AI-ification Agent. Analyze the chapter draft.

Chapter Content:
{chapter_content}

Audit Tasks:
1. Ensure 100% natural Vietnamese prose.
2. Strip AI cliches ('Tóm lại', 'Bức tranh toàn cảnh', 'Minh chứng cho', 'Lời kết', 'Trong thế giới này').
3. Verify narrative continuity and Xuanhuan/Xianxia tone.
4. Output ONLY the cleaned story text in natural Vietnamese.
"""

EXTRACT_ENTITIES_PROMPT = """
Read the following chapter and extract all character status updates, new characters, and lore.

Chapter Content:
{chapter_content}

Current Character States:
{current_characters}

Analyze and output a strict JSON object:
{{
  "new_characters": [
    {{
      "name": "Tên Nhân Vật Mới",
      "description": "Mô tả",
      "power_tier": "Cảnh giới tu luyện",
      "combat_stats": {{ "element": "Thuộc tính", "role": "Vai trò" }},
      "relationships": {{ "Tiêu Viêm": "Đồng minh/Kẻ thù" }}
    }}
  ],
  "character_updates": [
    {{
      "name": "Tiêu Viêm",
      "power_tier": "Cảnh giới hiện tại",
      "combat_stats": {{ "inventory": ["Vũ khí 1"] }},
      "relationships": {{ "Vân Vận": "Bằng hữu" }},
      "failure_flag": true,
      "breakthrough_written": false
    }}
  ],
  "new_lore": [
    {{ "keyword": "Từ khóa", "description": "Mô tả chi tiết" }}
  ]
}}
"""

REVIEW_PROMPT = """
You are a senior Xuanhuan novel editor. Review Chapter {chapter_number}: {chapter_title}.

Chapter Content:
{chapter_content}

Reference Lore: {world_lore}
Reference Characters: {characters}

Evaluation Standards:
1. Logic & Lore Consistency.
2. Pacing & Depth (No rushed scenes).
3. Xuanhuan Tropes (Did it use cultivation terms? Was combat epic?).
4. Cliffhanger ending.

Output a strict JSON object:
{{
  "pass_review": true,
  "score": 10,
  "feedback": "Detailed feedback",
  "violations": []
}}
"""

BRAINSTORM_PROMPT = """
You are a creative content producer. Brainstorm a Xianxia/Xuanhuan novel title and description.
Keep it in Vietnamese. Use rich cultivation terminology.
Output a JSON object:
{{
  "title": "Title",
  "description": "Description"
}}
"""

PLOT_EXPANSION_PROMPT = """
Dựa vào tiêu đề và tóm tắt, hãy viết một cốt truyện chi tiết (300-500 từ) phong cách Tiên Hiệp/Huyền Huyễn.
Hạn chế tên tiếng Anh, dùng tên thuần Việt hoặc Hán Việt.
Tiêu đề: {title}
Tóm tắt: {description}
"""
