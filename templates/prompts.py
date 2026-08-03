OUTLINE_PROMPT = """
You are the InkOS Radar & Architect Multi-Agent System (Narcooo InkOS Framework). Design a global master outline for an epic web novel spanning at least 150 chapters.
Target Audience: Teenagers and young adults (13-25 years old).
Title: {title}
Description: {description}

InkOS Architecture Directives:
1. Break down the entire story into 6-8 major Story Arcs (spanning 150+ chapters total).
2. Pacing: Deep world-building, slow-burn character growth, emotional resonance, and escalating stakes. Avoid rushing main plot points.
3. Character Naming Protocol: Use natural 2-word Vietnamese names ONLY (e.g. Minh Đức, Thùy Linh, Linh Vy, Trần Lam, Cao Bá). STRICTLY avoid using 3-word full names (do NOT use Nguyễn Minh Đức, Lê Thùy Linh) and NEVER use English proper nouns.
4. InkOS Audit Protocol: Establish 37-dimension narrative truth files (character growth, plot hooks, world lore rules, and emotional arcs).
5. Output a strictly formatted JSON object (no markdown wrappers):
{{
  "title": "Novel Title",
  "arcs": [
    {{
      "arc_number": 1,
      "title": "Arc Title",
      "summary": "Detailed summary of major conflicts, character transformations, and world revelations in this arc",
      "start_chapter": 1,
      "end_chapter": 25,
      "key_milestones": ["Major Milestone 1", "Major Milestone 2", "Arc Climax"]
    }}
  ]
}}
"""

ARC_PROMPT = """
You are the InkOS Planner & Architect Engine (Narcooo InkOS Framework). Create a detailed chapter-by-chapter blueprint outline for Arc {arc_number}: {arc_title} of the novel "{novel_title}".
Premise: {novel_description}
Arc Overview: {arc_summary}
Chapter Range: {start_chapter} to {end_chapter}
Global Story State: {global_status}

InkOS Directives:
1. Break down the arc into chapter blueprints. Each blueprint must specify the core conflict, characters involved, emotional beats, and a compelling hook.
2. Maintain slow-burn progression, realistic struggles, and high engagement.
3. Use natural 2-word Vietnamese names for all characters (e.g. Minh Đức, Thùy Linh, Linh Vy, Trần Lam). Strictly avoid 3-word full names and English proper nouns.
4. Output as a strictly formatted JSON array of chapters (no markdown wrappers):
[
  {{
    "chapter_number": 1,
    "chapter_title": "Chapter Title",
    "blueprint": "Detailed breakdown of the chapter events, character interactions, atmosphere, and cliffhanger setup",
    "characters_present": ["Trần Lam", "Linh Vy"],
    "narrative_goal": "Primary emotional or plot objective of this chapter"
  }}
]
"""

WRITING_PROMPT = """
You are the InkOS Writer & Composer Agent (Narcooo InkOS Multi-Agent Story Architecture). Write Chapter {chapter_number}: {chapter_title} of the novel "{title}".

INKOS TRUTH FILES & CONTEXT:
- Chapter Blueprint: {blueprint}
- World Lore & Rules: {world_lore}
- Character Bible & Status: {characters}
- Episodic History: {history}
- Previous Chapters Context: {previous_content}

INKOS 10-AGENT CORE DIRECTIVES (MUST FOLLOW AT ALL COSTS):
1. **WORD COUNT & EXPANSION**: Write a massive, immersive chapter exceeding 2500 - 3500 words (MUST BE >2200 WORDS minimum to yield 10+ minutes audio duration). Never summarize events. Write out every scene paragraph by paragraph in vivid detail.
2. **INKOS DE-AI-IFICATION & STYLE FINGERPRINT**:
   - STRICTLY ELIMINATE all AI clichés, filler phrases, and monotonous patterns (DO NOT write: 'Dẫn lược:', 'Tóm lại:', 'Bức tranh toàn cảnh', 'Minh chứng cho', 'Lời kết', 'Trong thế giới này').
   - Write with raw human narrative texture, micro-expressions, heartbeat acceleration, breath pauses, and atmospheric tension.
3. **SHOW, DON'T TELL & SENSORY GROUNDING**:
   - Describe sensory details: sound of wind rustling bamboo leaves, scent of rain-soaked earth, heartbeat pounding in chest, reflections of light on polished blades, micro-facial expressions, and subtle body posture.
   - Describe character internal monologues, doubts, strategic thoughts, and emotional weight in great depth.
4. **INKOS 5-STAGE CINEMATIC SCENE STRUCTURE**:
   - Stage 1: Atmospheric Opening & Environment Setup (300-500 words).
   - Stage 2: Rising Tension & Dialogue Encounter (600-800 words).
   - Stage 3: Core Confrontation or Mysterious Discovery (700-900 words).
   - Stage 4: Emotional & Physical Aftermath / Realization (500-700 words).
   - Stage 5: **HIGH-STAKES CLIFFHANGER**: End the chapter on a tense, unexpected twist or unresolved suspense that makes readers desperate for the next chapter!
5. **PROTAGONIST PROGRESSION & CONSTRAINT**:
   - Protagonist: {protagonist_name} | Current Power: {protagonist_power} | Stats: {protagonist_stats} | Failure Flag: {failure_flag}
   - **CRITICAL RULE**: The protagonist CANNOT level up or obtain new powers unless failure_flag is TRUE. If failure_flag is False, they must face intense struggle, difficulty, or setback without a breakthrough.
6. **NAMING & DIALOGUE STYLE**:
   - Use natural 2-word Vietnamese names ONLY (e.g. Trần Lam, Linh Vy, Minh Đức). NEVER use 3-word full names (do NOT write Nguyễn Minh Đức) and NEVER use English proper nouns.
   - **TẢI TRỌNG LỜI THOẠI ĐỐI THOẠI CỰC ĐẠI (70% - 80% DIRECT DIALOGUE RATIO)**: BẮT BUỘC câu chuyện phải chiếm từ 70% ĐẾN 80% LỜI NÓI TRỰC TIẾP và ĐỐI THOẠI giữa các nhân vật trong ngoặc kép ("..."). Mọi phân cảnh đều là sự đối đáp dồn dập, tranh luận gay gắt, khiêu khích, thì thầm, bàn chiến thuật và phản ứng bộc phát giữa nhân vật chính và các nhân vật xung quanh!

Write the chapter in natural, evocative Vietnamese. Output ONLY the raw story text without conversational intro/outro text, headers, or sections like 'Dẫn lược:' or 'Chương X:'. Write straight into the narrative.
"""

INKOS_AUDITOR_PROMPT = """
You are the InkOS Auditor & De-AI-ification Agent (Narcooo InkOS Framework). Analyze the following chapter draft and perform a 37-dimension quality audit.

Chapter Content:
{chapter_content}

Audit Tasks:
1. Strip all AI clichés (e.g., 'dẫn lược', 'tóm lại', 'tổng kết', 'bức tranh toàn cảnh', 'minh chứng').
2. Verify narrative continuity, dialogue flow, character memory consistency, and cliffhanger intensity.
3. If any AI clichés or repetitive sentences exist, rewrite and output the perfectly cleaned, enhanced chapter text.
4. Output ONLY the cleaned story text in natural Vietnamese.
"""

EXTRACT_ENTITIES_PROMPT = """
Read the following chapter and extract all character status updates, world lore additions, and active narrative threads.

Chapter Content:
{chapter_content}

Current Character States:
{current_characters}

Analyze the narrative and output a strictly formatted JSON object (no markdown wrappers):
{{
  "character_updates": [
    {{
      "name": "Trần Lam",
      "power_tier": "Novice",
      "combat_stats": {{ "attack": 15, "defense": 10 }},
      "relationships": {{ "Linh Vy": "ally" }},
      "failure_flag": true,
      "breakthrough_written": false
    }}
  ],
  "new_lore": [
    {{ "keyword": "Tinh Thần Ấn", "description": "Ấn ký bảo hộ cổ đại chứa sức mạnh các vị thần" }}
  ],
  "new_threads": [
    {{ "thread_name": "Bí Mật Chiếc Hộp Đông Sơn", "description": "Trần Lam tìm kiếm chìa khóa mở chiếc hộp cổ" }}
  ]
}}
"""

REVIEW_PROMPT = """
You are a senior novel editor. Review Chapter {chapter_number}: {chapter_title} for literary quality, depth, and consistency.

Chapter Content:
{chapter_content}

Reference Lore: {world_lore}
Reference Characters: {characters}
Protagonist Failure Flag: {failure_flag} | Last Breakthrough: {last_breakthrough_chapter}

Evaluation Standards:
1. **Logic & Lore Consistency**: Zero lore contradictions or character continuity errors.
2. **Pacing & Depth**: Deep slow-burn pacing with rich sensory details. No rushed plot points or skipped scenes.
3. **Progression Check**: Did the protagonist level up without failure_flag = true? (If yes, fail review).
4. **Vocabulary & Names**: 100% Vietnamese 2-word names. Zero 3-word full names, zero English proper nouns.
5. **Cliffhanger & Engagement**: High-stakes ending that compels readers to continue.

Output a strictly formatted JSON object:
{{
  "pass_review": true/false,
  "score": 1-10,
  "feedback": "Detailed editor feedback",
  "violations": ["List of specific violations if any"]
}}
"""

BRAINSTORM_PROMPT = """
You are a creative content producer. Brainstorm a completely original, highly compelling novel title and description targeted at teenagers (13-19 years old).
The genre can be Sci-Fi, High Fantasy, Cyberpunk, Isekai, or Magic Academy.

Requirements:
1. Brainstorm a cool and catchy title. Keep it in Vietnamese (e.g. "Kẻ Vô Năng Của Học Viện" or "Giao Thức Tĩnh Lặng").
2. The description must detail:
   - The world setting and its core magic/technology system.
   - The main protagonist (a teenager, starting weak or with a major handicap, facing challenges, slow growth, not overpowered).
   - The main conflict or driving force.
3. Use Vietnamese names for all characters (e.g., Phong, Nam, Vy, Linh) and Vietnamese terms for organizations and places. Avoid English names.
4. Output a JSON object with:
{
  "title": "Brainstormed Title",
  "description": "Detailed premise description"
}
Ensure the JSON is strictly formatted and valid. Do not wrap in markdown quotes.
"""

PLOT_EXPANSION_PROMPT = """
Dựa vào tiêu đề và tóm tắt ngắn dưới đây, hãy viết một cốt truyện chi tiết (khoảng 300-500 từ) bằng tiếng Việt cho tiểu thuyết này.
Nêu rõ bối cảnh thế giới, mâu thuẫn chính, và hành trình phát triển của nhân vật chính. 
Hạn chế sử dụng tên tiếng Anh hoặc danh từ riêng tiếng Anh. Hãy dùng tên thuần Việt (ví dụ: Trần Lam, Linh Vy...).

Tiêu đề: {title}
Tóm tắt ngắn: {description}

Cốt truyện chi tiết:
"""
