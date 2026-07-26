# Templates for AI Novel Writing Engine

OUTLINE_PROMPT = """
You are an expert story planner. Design a global outline for a web novel of at least 150 chapters.
The novel is targeted at teenagers (13-19 years old).
Title: {title}
Description: {description}

Requirements:
1. Divide the story into 6-8 major Story Arcs, totaling 150+ chapters.
2. Ensure slow-burn pacing, deep world-building, and character growth.
3. Avoid English names and English proper nouns. Use short 2-word Vietnamese names (e.g., Minh Đức, Thùy Linh, Linh Vy, Trần Lam). STRICTLY avoid using 3-word full names (e.g. do NOT use Nguyễn Minh Đức, Lê Thùy Linh). Keep all names natural and simple to Vietnamese readers.
4. Output the outline as a structured JSON object with the following schema:
{{
  "title": "Novel Title",
  "arcs": [
    {{
      "arc_number": 1,
      "title": "Arc Title",
      "summary": "Detailed summary of what happens in this arc",
      "start_chapter": 1,
      "end_chapter": 25,
      "key_milestones": ["Milestone 1", "Milestone 2"]
    }}
  ]
}}
Ensure the JSON is strictly formatted and valid. Do not wrap in markdown quotes.
"""

ARC_PROMPT = """
You are a detailed storyteller. Develop a chapter-by-chapter blueprint outline for Arc {arc_number}: {arc_title} of the novel "{novel_title}".
Novel Description: {novel_description}
Arc Summary: {arc_summary}
This arc spans chapters {start_chapter} to {end_chapter}.
Global story status: {global_status}

Requirements:
1. Break down the arc into individual chapters. For each chapter, outline the main event, key characters present, and narrative goals.
2. Maintain slow-burn, detailed pacing.
3. Avoid English names. Use short 2-word Vietnamese names for all characters (e.g. Minh Đức, Thùy Linh, Linh Vy, Trần Lam). STRICTLY avoid using 3-word full names (e.g. do NOT use Nguyễn Minh Đức, Lê Thùy Linh).
4. Output as a JSON array of chapters:
[
  {{
    "chapter_number": 1,
    "chapter_title": "Chapter Title",
    "blueprint": "Detailed description of what needs to happen in this chapter",
    "characters_present": ["Jack", "Alex"],
    "narrative_goal": "Goal of this chapter"
  }}
]
Ensure the JSON is valid.
"""

WRITING_PROMPT = """
You are an elite novelist. Write Chapter {chapter_number}: {chapter_title} of the novel {title}.
The target audience is teenagers. The pacing must be detailed, slow-burn, focusing on deep scene descriptions, atmospheric building, and detailed dialogues. Do not rush the plot.

Context and Resources:
- Chapter Blueprint: {blueprint}
- World Rules & Lore: {world_lore}
- Character Bible: {characters}
- Episodic History (Previous Arcs): {history}
- Previous Chapters Context: {previous_content}

Constraints:
1. Word count: Write a massive chapter of at least 2500 to 3500 words (MUST exceed 2200 words at all costs to ensure a full 10+ minutes speaking time). Describe environments, character body language, internal thoughts, and detailed conversations in great depth. Avoid summarizing any action or event. Write out every single interaction in detailed, paragraph-by-paragraph scenes.
2. Tone & Vocabulary: Avoid English proper nouns and English names. Use short 2-word Vietnamese names for characters (e.g., Minh Đức, Thùy Linh, Linh Vy, Trần Lam) and avoid using 3-word full names (do NOT use Nguyễn Minh Đức, Lê Thùy Linh). Keep all Vietnamese terminology natural.
3. Protagonist Progression: The protagonist ({protagonist_name}) currently has power level: {protagonist_power} and stats: {protagonist_stats}.
   - **CRITICAL**: The protagonist CANNOT level up or obtain new powers in this chapter unless the failure flag is TRUE (failure_flag = {failure_flag}).
   - If failure_flag is False, the protagonist must face challenging obstacles, struggle, or experience setbacks without a breakthrough. Keep their powers exactly as is.
4. Dialogue: Make the conversation between characters dynamic and teenager-friendly (50% dialogue/action, 50% description).

Write the chapter in Vietnamese. Keep the output as the raw novel content only (do not include conversational chat filler or introduction like "Here is the chapter...", but DO write the prologue/story introduction if it is part of the chapter content).
"""

EXTRACT_ENTITIES_PROMPT = """
Read the following chapter and extract any updates to the character status, relationships, world lore, or new narrative threads.

Chapter Content:
{chapter_content}

Current Character States:
{current_characters}

Analyze the chapter and output a JSON object indicating:
1. Whether any character's power level, combat stats, or relationships updated.
2. Whether the protagonist experienced a major defeat, setback, or failure (set failure_flag to true if they failed/lost/struggled heavily, or keep false).
3. If the protagonist had a breakthrough (breakthrough = true if they leveled up or unlocked new powers, otherwise false).
4. Any new lore keywords introduced.
5. Any new active narrative threads.

Output format (strict JSON, do not wrap in markdown):
{{
  "character_updates": [
    {{
      "name": "Jack",
      "power_tier": "Novice",
      "combat_stats": {{ "attack": 15, "defense": 10 }},
      "relationships": {{ "Alex": "ally" }},
      "failure_flag": true,
      "breakthrough_written": false
    }}
  ],
  "new_lore": [
    {{ "keyword": "Aetheria", "description": "A floating city in the sky" }}
  ],
  "new_threads": [
    {{ "thread_name": "The Missing Key", "description": "Jack needs to find the key to the Cortex Engine" }}
  ]
}}
"""

REVIEW_PROMPT = """
You are a senior novel editor. Review Chapter {chapter_number}: {chapter_title} for quality and consistency.

Chapter Content:
{chapter_content}

Reference World Rules and Lore:
{world_lore}

Reference Character Bible:
{characters}

Protagonist State:
- failure_flag: {failure_flag}
- last_breakthrough_chapter: {last_breakthrough_chapter}

Analyze the chapter and answer the following questions:
1. **Logic Contradiction**: Does the chapter contradict any established world lore or character profiles? (e.g. eye color change, weapon name mismatch, dead character appearing).
2. **Pacing Check**: Is the pacing too fast or rushed? (e.g. traveling across a kingdom in a single paragraph, defeating a boss in two sentences). It must be detailed and slow-burn.
3. **Protagonist Progression Check**: Did the protagonist obtain a breakthrough or easily defeat an opponent?
   - If failure_flag is false: Did the protagonist break this constraint and level up anyway? (This is a violation).
   - Did the protagonist win a major fight too easily?
4. **Vocabulary Check**: Are any character names or proper nouns in English? (Prefer Vietnamese names and terms. Avoid English names).

Output a JSON response:
{{
  "pass_review": true/false,
  "score": 1-10,
  "feedback": "Detailed feedback of issues found",
  "violations": ["List of specific violations like 'Protagonist leveled up without failure flag' or 'Rushed pacing'"]
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
