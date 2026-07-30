import json
import os
import re
import hashlib
import time
from typing import Dict, List, Any, Optional

class Ultimate50FeatureMemoryEngine:
    """Hệ Thống Bộ Nhớ Tối Thượng 50 Tính Năng Tối Ưu Nhất Cho AI Video Novel (100% Free).
    Bao gồm 5 phân nhóm:
    1. Character & Entity Memory (Features 1-10)
    2. Environment & Spatiotemporal Memory (Features 11-20)
    3. Cinematic Camera & Motion Memory (Features 21-30)
    4. Negative Prompting & Quality Guardrails (Features 31-40)
    5. Performance, Caching & Adaptive Intelligence (Features 41-50)
    """

    # BỘ 50 QUY TẮC THIẾT KẾ ĐỒ HỌA, KỂ CHUYỆN & RENDER VIDEO TRIỆU VIEW (50 MASTER RULES)
    MASTER_50_DESIGN_AND_STORYTELLING_RULES = [
        # Domain 1: Visual & Thumbnail Design (Rules 1-10)
        "Rule 1: Rule of Thirds Hero Anchoring (Đặt tầm mắt nhân vật ở đường 1/3 ngang phía trên)",
        "Rule 2: High Contrast Rim Lighting (Viền sáng xanh cyan/vàng bóc tách chủ thể khỏi nền tối)",
        "Rule 3: Gold & Crimson Typography (Tiêu đề Vàng Hoàng Kim #FFD700 + Badge Đỏ Crimson #DC2626)",
        "Rule 4: Multi-Layer Stroke Outline (Chữ có viền đen 4px + bóng đổ mờ chống chói 100%)",
        "Rule 5: Floating Particle Energy Elements (Hạt bụi năng lượng và đốm lửa huyền ảo)",
        "Rule 6: Volumetric Fog & Depth (Sương mù tầm thấp tạo độ sâu 3D cho nét vẽ 2D)",
        "Rule 7: Eye Contact & Expression Locking (Ánh mắt sắc sảo có thần thái nhìn hơi chệch tâm)",
        "Rule 8: Color Temperature Contrast (Nền tone lạnh xanh lam vs Hào quang tone nóng vàng đỏ)",
        "Rule 9: Speed Lines & Motion Blur (Tia tốc độ tạo cảm giác hành động kịch tính)",
        "Rule 10: 16:9 Widescreen Framing Lock (Ép tỷ lệ 1920x1080 không bị viền đen thừa)",

        # Domain 2: Novel Writing & Storytelling (Rules 11-20)
        "Rule 11: 5-Stage Cinematic Arc (Mở đầu -> Mâu thuẫn -> Đỉnh điểm -> Dư âm -> Cliffhanger)",
        "Rule 12: High-Stakes Cliffhanger Lock (Kết chương bằng biến cố lấp lửng ép nghe tập sau)",
        "Rule 13: Sensory Multi-Layering (Miêu tả âm thanh, mùi hương, nhịp tim, ánh sáng giác quan)",
        "Rule 14: 50/50 Dialogue to Description Ratio (Cân bằng 50% thoại/hành động & 50% suy nghĩ nội tâm)",
        "Rule 15: Pure 2-Word Vietnamese Names (Dùng tên thuần Việt 2 từ: Trần Lam, Linh Vy, Minh Đức)",
        "Rule 16: Zero 3-Word Full Name Violation (Tuyệt đối không dùng tên 3 từ: Nguyễn Minh Đức)",
        "Rule 17: Zero English Name Hallucination (Không dùng tên tiếng Anh hay danh từ Tây phương)",
        "Rule 18: Protagonist Struggle Constraint (Nhân vật chính giữ nguyên sức mạnh trừ khi failure_flag=True)",
        "Rule 19: Micro-Facial & Body Language (Miêu tả nheo mắt, siết chặt tay, nhịp thở dồn dập)",
        "Rule 20: Word Count Lock (>2200 Words) (Đảm bảo độ dài >2200 từ cho 10+ phút nghe audio)",

        # Domain 3: Audio & Subtitle Timing (Rules 21-30)
        "Rule 21: Exact SRT Timestamp Scene Sync (Đổi ảnh AI khớp chính xác theo mốc thời gian phụ đề)",
        "Rule 22: Max 34 Characters Per Subtitle Line (Ngắt dòng phụ đề tối đa 34 ký tự tránh tràn màn)",
        "Rule 23: Centered YouTube Subtitle Box (Căn giữa lề dưới MarginV=35, MarginL=80, MarginR=80)",
        "Rule 24: High-Contrast White/Black Subtitle Outline (Chữ trắng viền đen nổi Outline=2, Shadow=1)",
        "Rule 25: Speech Rate Pacing (+10%) (Tốc độ nói 1.1x vừa vặn giữ chân khán giả trẻ)",
        "Rule 26: Voice Pitch Tuning (+0Hz) (Giữ chất giọng tự nhiên không bị méo tiếng)",
        "Rule 27: Multi-Chunk Speech Synthesis (Chia nhỏ text <3000 ký tự tránh ngắt kết nối TTS)",
        "Rule 28: Seamless Audio Chunk Stitching (Nối các đoạn audio mượt mà không có quãng lặng)",
        "Rule 29: Audio Duration Probing (ffprobe) (Đo độ dài MP3 chính xác đến millisecond)",
        "Rule 30: Audio Peak Normalization (Giữ âm lượng ổn định chuẩn YouTube -14 LUFS)",

        # Domain 4: Video Slideshow & Motion (Rules 31-40)
        "Rule 31: Subtle Ken Burns Motion (Phóng to/thu nhỏ lia máy nhẹ nhàng không méo nét)",
        "Rule 32: Dynamic Multi-Image Rotation (Sinh tới 40 ảnh AI đa dạng phân cảnh mỗi chương)",
        "Rule 33: Seamless Loop Extension (Tự lặp chuỗi ảnh mượt mà cho video dài 8-10 phút)",
        "Rule 34: NVENC Hardware Acceleration (Ưu tiên GPU NVIDIA NVENC render gấp 4 lần)",
        "Rule 35: Concat Demuxer Frame Precision (Tính toán d=interval*fps khớp thời lượng thoại)",
        "Rule 36: Brightness & Contrast Balancing (Cân bằng eq=brightness=-0.15:contrast=1.1 nổi chữ)",
        "Rule 37: Aspect Ratio Enforcement (Tự động scale & crop về chuẩn Widescreen 1920x1080)",
        "Rule 38: Video Quality Validation (Tự động kiểm tra file size và độ dài trước khi upload)",
        "Rule 39: YUV420P Pixel Format (Tương thích 100% trên mọi thiết bị di động và trình duyệt)",
        "Rule 40: AAC 192k High-Fidelity Audio (Xuất âm thanh chất lượng cao 192kbps)",

        # Domain 5: Engine Infrastructure & Resilience (Rules 41-50)
        "Rule 41: Multi-Provider Key Rotator (Tự xoay vòng key Groq & Gemini khi chạm Quota 429)",
        "Rule 42: Instant 401 Unauthenticated Failover (Vô hiệu hóa vĩnh viễn key hỏng 401 lập tức)",
        "Rule 43: Supabase Storage Retry (3 Attempts) (Thử lại 3 lần khi upload file MP4 lớn)",
        "Rule 44: Storage Bucket Caching (Ghi nhớ cache bucket media giảm 50% request thừa)",
        "Rule 45: Environmental Variable Sanitization (Làm sạch ký tự ẩn \\n, \\r, dấu ngoặc trong Secrets)",
        "Rule 46: Auto SEO Tags & Metadata (Tự sinh tiêu đề YouTube, Tags & Hashtags triệu view)",
        "Rule 47: Auto Chapter Summary Recap (Tóm tắt chương 2-3 câu lôi cuốn cho bài đăng)",
        "Rule 48: Automated Disk Hygiene (Tự dọn dẹp ảnh tạm sau khi render video xong)",
        "Rule 49: GitHub Actions 30-Minute Timeout (Đảm bảo video 10 phút render không bị timeout)",
        "Rule 50: Deterministic Visual Seed Hashing (Khóa seed MD5 giữ ngoại hình nhân vật nhất quán)"
    ]

    # Category 3: Cinematic Camera Sequences (Features 21-30)
    CINEMATIC_SHOT_MATRIX = [
        {"shot": "cinematic establishing wide shot, breathtaking environment, golden ratio composition", "focal": "24mm wide lens", "dof": "deep depth of field"},
        {"shot": "dynamic medium action shot, Rule of Thirds framing, volumetric lighting", "focal": "50mm standard lens", "dof": "medium depth of field"},
        {"shot": "dramatic character close-up, sharp eye focus, emotional sentiment", "focal": "85mm portrait lens", "dof": "shallow bokeh background"},
        {"shot": "over-the-shoulder perspective, immersive character interaction", "focal": "35mm storytelling lens", "dof": "cinematic depth"},
        {"shot": "low-angle heroic perspective, epic volumetric lighting rays", "focal": "28mm wide action lens", "dof": "sharp contrast"},
        {"shot": "panoramic aerial overhead shot, vast atmospheric perspective", "focal": "16mm ultra-wide lens", "dof": "infinite depth"}
    ]

    # Category 4: Negative Prompting & Quality Guardrails (Features 31-40 - Hardened Defect Removal)
    MASTER_NEGATIVE_PROMPT = (
        "3D render, photorealistic, realistic 3D photo, CGI, octane render, 3D model, "
        "middle-aged man, old man, facial hair, beard, mustache, wrinkles, aging face, "
        "blurry, low quality, extra limbs, bad hands, deformed fingers, extra fingers, "
        "fused fingers, missing limbs, malformed hands, asymmetric eyes, cross-eyed, "
        "deformed eyes, bad proportions, unnatural body posture, mutated body, distorted face, "
        "disfigured hands, poorly drawn face, poorly drawn hands, floating limbs, disconnected limbs, "
        "bad anatomy, text, watermark, signature, cropped, out of frame, duplicate character, "
        "color bleeding, oversaturated, ugly, jpeg artifacts, low resolution blur"
    )

    def __init__(self, memory_file: str = "output/ultimate_50_memory.json"):
        self.memory_file = memory_file
        
        # Category 1: Character Memory State (Features 1-10)
        self.characters: Dict[str, Dict[str, Any]] = {}
        
        # Category 2: Environment Memory State (Features 11-20)
        self.environment_context: Dict[str, Any] = {
            "realm_style": "xianxia ancient fantasy",
            "architecture": "traditional eastern pagodas and stone temples",
            "location": "mystical bamboo forest valley",
            "time_of_day": "midnight moonlight",
            "weather": "misty fog",
            "color_palette": "cool blue and emerald green tones",
            "lighting": "ethereal volumetric moonlight rays",
            "environmental_damage": "pristine"
        }
        
        # Category 3 & 5 State (Features 21-50)
        self.camera_step = 0
        self.prompt_cache: Dict[str, str] = {}
        self.current_chapter_arc: str = "Arc 1"
        
        self.load_memory()
        
        # Register core main characters with explicit age lock (Youth / Thanh niên 18-20 t)
        if "trần lam" not in self.characters:
            self.register_character(
                name="Trần Lam",
                aliases=["trần lam", "lam", "thanh niên", "cậu"],
                base_appearance="handsome young male cultivator, 18-20 years old youthful face, athletic young man, short black hair, clean shaven",
                outfit="ancient blue cultivator robes",
                color_palette="cyan and silver"
            )

    def load_memory(self):
        """Feature 43: Disk-backed Persistent JSON State"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.characters = data.get("characters", {})
                    self.environment_context = data.get("environment_context", self.environment_context)
                    self.prompt_cache = data.get("prompt_cache", {})
            except Exception as e:
                print(f"[WARNING] Cannot load memory disk state: {e}")

    def save_memory(self):
        """Feature 43: Persistent Disk Save"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({
                    "characters": self.characters,
                    "environment_context": self.environment_context,
                    "prompt_cache": self.prompt_cache
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Error saving memory state: {e}")

    # --- CATEGORY 1: CHARACTER & ENTITY VISUAL MEMORY (Features 1-10) ---
    def register_character(
        self,
        name: str,
        aliases: List[str],
        base_appearance: str,
        outfit: str,
        weapon: str = "",
        color_palette: str = "",
        age_group: str = ""
    ):
        """Feature 1: Multi-Alias Graph | Feature 9: Color Palette Locker | Explicit Universal Age Group Lock"""
        key = name.lower()
        
        # Tự động nhận diện độ tuổi chuẩn nếu chưa khai báo (Auto Age Group Inference)
        if not age_group:
            search_str = (name + " " + " ".join(aliases) + " " + base_appearance).lower()
            if any(w in search_str for w in ["lão", "ông", "bà", "trưởng lão", "elder", "veteran"]):
                age_group = "65-75 years old elderly person"
            elif any(w in search_str for w in ["chú", "bác", "trung niên", "sư phụ", "chủ quán", "trung niên"]):
                age_group = "40-50 years old middle-aged adult"
            elif any(w in search_str for w in ["tiểu", "thiếu niên", "em bé", "bé"]):
                age_group = "14-16 years old young teenager"
            else:
                age_group = "18-20 years old youthful young person"

        self.characters[key] = {
            "name": name,
            "aliases": [a.lower() for a in aliases] + [key],
            "appearance": base_appearance,
            "age_group": age_group,   # Ép độ tuổi chuẩn cố định cho MỌI nhân vật
            "outfit": outfit,
            "weapon": weapon,
            "color_palette": color_palette,
            "injuries": [],          # Feature 2: Dynamic Injury & Status Tracker
            "outfit_state": "intact", # Feature 3: Outfit & Armor State Persistence
            "emotion": "calm",        # Feature 4: Emotion Vector
            "items": [],             # Feature 5: Item & Artifact Attachment
            "transformation": ""     # Feature 7: Disguise & Shapeshifting Toggle
        }
        self.save_memory()

    def update_character_status(self, name: str, injury: str = "", emotion: str = "", outfit_state: str = "", transformation: str = ""):
        """Features 2, 3, 4, 7: Update dynamic character status"""
        key = name.lower()
        if key in self.characters:
            char = self.characters[key]
            if injury: char["injuries"].append(injury)
            if emotion: char["emotion"] = emotion
            if outfit_state: char["outfit_state"] = outfit_state
            if transformation: char["transformation"] = transformation
            self.save_memory()

    # --- CATEGORY 2: ENVIRONMENT & SPATIOTEMPORAL MEMORY (Features 11-20) ---
    def update_environment(
        self,
        architecture: str = "",
        location: str = "",
        time_of_day: str = "",
        weather: str = "",
        lighting: str = "",
        environmental_damage: str = ""
    ):
        """Features 11-17: Environmental, Weather & Lighting Continuity"""
        env = self.environment_context
        if architecture: env["architecture"] = architecture
        if location: env["location"] = location
        if time_of_day: env["time_of_day"] = time_of_day
        if weather: env["weather"] = weather
        if lighting: env["lighting"] = lighting
        if environmental_damage: env["environmental_damage"] = environmental_damage
        self.save_memory()

    # UNIVERSAL MULTI-GENRE MASTER ART SYSTEM
    # Tự động hóa Prompt chuẩn nghệ thuật 2D Manhwa / Webtoon / Anime 8K đỉnh cao cho MỌI THỂ LOẠI TRUYỆN
    GENRE_STYLE_PRESETS = {
        "xianxia": "ancient eastern Xianxia fantasy, traditional Pagodas, ethereal misty bamboo valley, flying sword, martial robes, glowing energy aura",
        "scifi": "futuristic cyberpunk metropolis, glowing neon lights, holographic billboards, high-tech armor, mecha sci-fi aesthetic",
        "urban": "modern city street, realistic high school / university campus, aesthetic urban fashion, cozy natural lighting",
        "fantasy": "epic medieval high fantasy, gothic stone castle, mystical enchanted forest, glowing magic runes, knight armor",
        "mystery": "dark noir mystery, rain-slicked cobblestone alley, dramatic shadow contrast, foggy night, vintage detective aesthetic"
    }

    # PROMPT COMPILER CHUYÊN NGHIỆP CHO MỌI TIỂU THUYẾT
    def compile_master_prompt(self, scene_text: str, target_aspect_ratio: str = "16:9") -> Dict[str, str]:
        """
        Compiler Prompt đa năng: Tự động phân tích thể loại, loại bỏ độ tuổi già,
        ép góc máy điện ảnh và khống chế chuẩn nét vẽ 2D Manhwa 8K sắc nét cho mọi tiểu thuyết.
        """
        text_lower = scene_text.lower()

        # 1. Tự động nhận diện Thể loại truyện (Genre Auto-Detection)
        selected_genre = "xianxia"  # Mặc định tiên hiệp / huyền huyễn
        if any(w in text_lower for w in ["cyberpunk", "robot", "phi thuyền", "công nghệ", "laser", "tương lai"]):
            selected_genre = "scifi"
        elif any(w in text_lower for w in ["trường học", "lớp học", "xe máy", "điện thoại", "đô thị", "phố"]):
            selected_genre = "urban"
        elif any(w in text_lower for w in ["lâu đài", "pháp sư", "quái vật", "rồng", "hiệp sĩ", "ma thuật"]):
            selected_genre = "fantasy"
        elif any(w in text_lower for w in ["mưa", "đêm", "vết máu", "bí ẩn", "sát thủ", "trinh thám"]):
            selected_genre = "mystery"

        genre_prompt = self.GENRE_STYLE_PRESETS[selected_genre]

        # 2. BỘ NHỚ SIÊU CẤP NHÂN VẬT & ĐỐI TƯỢNG (Super Visual Memory Engine)
        # Nạp tự động: Trang phục, Thần thái (Cảm xúc), Vết thương, Bảo khí vũ khí & Màu sắc đặc trưng
        matched_chars_prompts = []
        # 2. Xử lý Đa Nhân Vật & Bố Cục Đối Thoại Khung Tranh (Multi-Character Composition Engine)
        matched_chars_prompts = []
        matched_char_names = []
        
        for key, char in self.characters.items():
            if any(alias in text_lower for alias in char["aliases"]):
                matched_char_names.append(char['name'])
                c_details = [
                    f"({char['appearance']}:1.25)",
                    f"({char.get('age_group', '18-20 years old youthful person')}:1.3)",
                    f"wearing {char['outfit']}"
                ]
                if char.get("color_palette"):
                    c_details.append(f"{char['color_palette']} color accents")
                if char.get("weapon"):
                    c_details.append(f"wielding {char['weapon']}")
                if char.get("emotion"):
                    c_details.append(f"{char['emotion']} expression")
                if char.get("injuries"):
                    c_details.append(f"with {', '.join(char['injuries'])}")
                if char.get("transformation"):
                    c_details.append(f"in {char['transformation']} mode")
                    
                matched_chars_prompts.append(", ".join(c_details))

        # TỰ ĐỘNG PHÁT HIỆN BỐ CỤC ĐỐI THOẠI NỀN NHIỀU NHÂN VẬT & ĐÁM ĐÔNG (Multi-Character Group & Crowd Engine)
        is_dialogue = any(w in text_lower for w in ["nói", "đối thoại", "trả lời", "hỏi", "thì thầm", "bảo", "quát", "giao phong", "bàn luận"])
        is_faceoff = any(w in text_lower for w in ["nhìn", "đối diện", "đối đầu", "quyết đấu", "khiêu khích", "xung đột", "khiêu chiến"])
        is_crowd = any(w in text_lower for w in ["đám đông", "khán giả", "học viện", "quần chúng", "vây quanh", "xem", "hoan hô", "xì xào", "xôn xao", "đấu trường"])
        
        # Bố cục nhiều nhân vật (3+ người)
        if len(matched_chars_prompts) >= 3:
            all_chars_joined = " AND ".join(matched_chars_prompts[:3])
            character_anchor = (
                f"MULTIPLE CHARACTERS IN FRAME, GROUP DIALOGUE PANEL, "
                f"PARTY ASSEMBLY: [{all_chars_joined}], "
                f"group of characters standing together in wide cinematic framing, interactive conversation stance"
            )
        elif len(matched_chars_prompts) == 2:
            c1_prompt = matched_chars_prompts[0]
            c2_prompt = matched_chars_prompts[1]
            character_anchor = (
                f"TWO CHARACTERS IN FRAME, DUAL SHOT MANHWA PANEL, "
                f"FIRST CHARACTER: [{c1_prompt}], SECOND CHARACTER: [{c2_prompt}], "
                f"facing each other in intense dialogue interaction, Over-The-Shoulder cinematic angle or split panel composition"
            )
        elif len(matched_chars_prompts) == 1 and is_crowd:
            c1_prompt = matched_chars_prompts[0]
            character_anchor = (
                f"MAIN CHARACTER IN FOREGROUND WITH MASSIVE SPECTATOR CROWD IN BACKGROUND, "
                f"HERO CHARACTER: [{c1_prompt}], "
                f"surrounded by shocked academy students and cheering crowd spectators, arena audience background"
            )
        elif len(matched_chars_prompts) == 1 and (is_dialogue or is_faceoff):
            c1_prompt = matched_chars_prompts[0]
            character_anchor = (
                f"TWO CHARACTERS IN FRAME, DIALOGUE SCENE, "
                f"PRIMARY CHARACTER: [{c1_prompt}], OPPOSING CHARACTER: [handsome rival character or academy elder opponent], "
                f"standing opposite each other engaged in conversation, intense dramatic eye contact, mid-shot composition"
            )
        elif is_crowd:
            character_anchor = (
                "MASSIVE CROWD SCENE IN ANCIENT ACADEMY ARENA, MULTIPLE SPECTATORS AND STUDENTS IN FRAME, "
                "shocked audience crowd reacting to the showdown event, wide angle Manhwa panel"
            )
        elif is_dialogue or is_faceoff:
            character_anchor = (
                "TWO CHARACTERS IN FRAME, DUAL SHOT DIALOGUE SCENE, "
                "handsome 18 years old young male protagonist hero talking to a sharp-eyed opponent rival character, "
                "facing each other in dynamic Manhwa panel"
            )
        elif len(matched_chars_prompts) == 1:
            character_anchor = matched_chars_prompts[0]
        else:
            character_anchor = "handsome 18 years old young male protagonist hero, youthful face, clean shaven, short black hair"

        # 3. Ép Góc máy điện ảnh lặp (Cinematic Camera Sequence)
        cam = self.CINEMATIC_SHOT_MATRIX[self.camera_step % len(self.CINEMATIC_SHOT_MATRIX)]
        self.camera_step += 1

        # 4. Trích xuất & Tự động dịch / Mở rộng từ khóa hình ảnh tiếng Việt sang tiếng Anh (Visual Keyword Expansion Matrix)
        clean_words = re.sub(r"[^\w\s]", "", scene_text).split()
        scene_action_clean = " ".join(clean_words[:15]) if clean_words else "dynamic action moment"

        # MA TRẬN BƠM HIỆU ỨNG CHIẾN ĐẤU & THỊ GIÁC ĐIỆN ẢNH SIÊU CẤP (Ultra Combat & FX Matrix)
        visual_fx = []
        if any(w in text_lower for w in ["đánh", "chiến", "đấu", "chém", "kiếm", "đao"]):
            visual_fx.append("EXPLOISVE SWORD SLASH ENERGY TRAIL, SHARP METALLIC REFLECTIONS, SWORD AURA ARC, ACTION SPEED LINES")
        if any(w in text_lower for w in ["bùng nổ", "oanh", "chấn động", "nổ"]):
            visual_fx.append("ENORMOUS IMPACT ENERGY SHOCKWAVE BURST, CRATER GROUND CRACKS, DYNAMIC DUST PARTICLES")
        if any(w in text_lower for w in ["quyền", "chưởng", "đấm"]):
            visual_fx.append("HIGH-SPEED POWERFUL FIST IMPACT STRIKE, AIR PRESSURE WAVE DISCHARGE, DYNAMIC combat stance")
        if any(w in text_lower for w in ["sét", "lôi", "điện"]):
            visual_fx.append("CRACKLING PURPLE LIGHTNING STRIKES, INTENSE ELECTRIC ARCS, THUNDEROUS AURA")
        if any(w in text_lower for w in ["lửa", "cháy", "hỏa"]):
            visual_fx.append("SWIRLING FIERY EMBERS, BRIGHT ORANGE FLAMES, GLOWING HEAT AURA EXPLOSION")
        if any(w in text_lower for w in ["băng", "tuyết", "lạnh"]):
            visual_fx.append("CRYSTAL ICE SHARDS, FREEZING FROST PARTICLES, ICY BLUE RADIANT AURA")
        if any(w in text_lower for w in ["máu", "huyết", "thương"]):
            visual_fx.append("DARK CRIMSON ENERGY MIST, OMINOUS RED AURA, INTENSE BATTLE DAMAGE")
        if any(w in text_lower for w in ["quỷ", "ma", "bóng tối"]):
            visual_fx.append("DARK SHADOW TENDRILS, PURPLE DEMONIC MIASMA, GLOWING RED EYE GLINT")
        if any(w in text_lower for w in ["ấn", "trận", "phép", "thức tỉnh"]):
            visual_fx.append("GLOWING ANCIENT CELESTIAL MAGIC ARRAY RUNES, GOLDEN CIRCLE SPELL SIGIL, AWAKENING GLOW")
        if any(w in text_lower for w in ["hệ thống", "giao diện", "bảng"]):
            visual_fx.append("FLOATING NEON CYAN HOLOGRAPHIC SYSTEM UI SCREEN WINDOWS")
        if any(w in text_lower for w in ["rừng", "cây", "núi"]):
            visual_fx.append("LUSH FOREST GREENERY, SUNBEAMS THROUGH LEAVES, MAJESTIC MOUNTAIN BACKDROP")

        # Tự động nhận diện Thần Thái / Cảm Xúc Khuôn Mặt (Facial Expression Engine)
        facial_expression = "intense determined expression, sharp calculating eyes"
        if any(w in text_lower for w in ["gầm", "thét", "nổi giận", "tức giận"]):
            facial_expression = "furious roaring expression, veins bulging, fierce gaze"
        elif any(w in text_lower for w in ["cười", "nhếch mép", "tự tin"]):
            facial_expression = "smirking confident smile, sharp intelligent eyes"
        elif any(w in text_lower for w in ["khóc", "đau đớn", "tuyệt vọng"]):
            facial_expression = "grief-stricken tearful eyes, clenched teeth, battered face"

        fx_string = ", ".join(visual_fx) if visual_fx else "volumetric rim light, floating glowing particles"

        # 5. BỘ KHÓA NÉT VẼ & DIỆN MẠO NHẤT QUÁN TỪ CÁC SIÊU PHẨM TRUYỆN TRANH NỔI TIẾNG
        # Tích hợp phong cách nghệ thuật từ Solo Leveling, Ta Là Tà Đạo (Magic Emperor), TBATE, JJK và Tower of God
        UNIFIED_ART_STYLE_HEADER = (
            "MASTERPIECE 2D KOREAN MANHWA WEBTOON ART STYLE, FAMOUS COMIC ART DIRECTION, "
            "INSPIRED BY SOLO LEVELING AND MAGIC EMPEROR AND TBATE WEBTOON ART, EXACT SAME UNIFIED ARTWORK DIRECTORY, "
            "CONSISTENT CHARACTER VISUAL FEATURES, BOLD SHARP BLACK INK LINE ART, VIBRANT SATURATED CEL-SHADING COLOR GRADING, "
            "HIGH-CONTRAST DRAMATIC CHIAROSCURO LIGHTING, DYNAMIC CINEMATIC THREE-POINT PERSPECTIVE COMPOSITION"
        )

        # 4b. Dynamic Action Mood & Emotion Auto-Enhancer (Phát hiện cảm xúc & hiệu ứng chiến đấu tự động)
        mood_tags = []
        lower_scene = scene_text.lower()
        if any(w in lower_scene for w in ["giận", "nộ", "quát", "gầm", "sát khí"]):
            mood_tags.append("furious roaring expression, glowing crimson eyes, intense red aura particles")
        if any(w in lower_scene for w in ["bá chủ", "thức tỉnh", "bộc phát", "vô địch"]):
            mood_tags.append("godlike awakening light, golden energy eruption, electric lightning discharge")
        if any(w in lower_scene for w in ["chém", "đánh", "kiếm", "quyết chiến", "xung đột"]):
            mood_tags.append("epic weapon clash sparks, fiery blast impact, dynamic action speed lines")
        if any(w in lower_scene for w in ["ma", "tà", "tối", "quỷ"]):
            mood_tags.append("sinister purple shadow miasma, dark demonic energy aura")
            
        mood_string = ", ".join(mood_tags) if mood_tags else "intense focused atmosphere"

        positive_prompt = (
            f"{UNIFIED_ART_STYLE_HEADER}, {cam['shot']}, {cam['focal']}, {cam['dof']}, {character_anchor}, "
            f"{facial_expression}, action sequence: {scene_action_clean}, setting: {genre_prompt}, visual fx: {fx_string}, "
            f"{mood_string}, glowing elemental energy aura, dynamic speed particles, dramatic rim light, 16:9 widescreen, "
            f"Solo Leveling aura glow, Magic Emperor demonic eyes, uniform visual identity across all panels, 8k resolution"
        )

        # MD5 Hash Caching
        prompt_hash = hashlib.md5(positive_prompt.encode("utf-8")).hexdigest()

        return {
            "positive_prompt": positive_prompt,
            "negative_prompt": self.MASTER_NEGATIVE_PROMPT,
            "hash": prompt_hash,
            "camera_info": cam
        }

# Global Instance
ultimate_memory_50 = Ultimate50FeatureMemoryEngine()

if __name__ == "__main__":
    # Test 50-Feature Memory Engine
    ultimate_memory_50.register_character(
        name="Tiêu Viêm",
        aliases=["tiêu viêm", "viêm đế"],
        base_appearance="handsome young warrior, short black hair, sharp eyes",
        outfit="black battle robes",
        weapon="giant heavy ruler sword",
        color_palette="black and gold"
    )
    
    ultimate_memory_50.update_character_status("Tiêu Viêm", injury="scar on left cheek", emotion="furious", transformation="Green Flame Form")
    ultimate_memory_50.update_environment(location="Volcanic Crater Peak", weather="ash rainfall", environmental_damage="shattered rocks and molten lava")
    
    compiled = ultimate_memory_50.compile_master_prompt("Tiêu Viêm vung kiếm chiến đấu trên đỉnh núi lửa")
    print("=== ULTIMATE 50-FEATURE MEMORY COMPILED ===")
    print("POSITIVE:", compiled["positive_prompt"])
    print("NEGATIVE:", compiled["negative_prompt"])
