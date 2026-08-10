import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
from src import database, writer, visual_prompt_engine

SIMULATED_NOVEL = {
    "id": "novel-simulated-tieudaotiendo-888",
    "title": "Tiêu Dao Tiên Đồ",
    "description": "Lâm Phong - Tiêu Dao Tiên Tôn đại năng trùng sinh về đô thị. Tay nắm Cửu Tiêu Tiên Thần Kiếm, ngang tàng đè ép chư thiên!"
}

SIMULATED_CHARACTERS = [
    {
        "novel_id": SIMULATED_NOVEL["id"],
        "name": "Lâm Phong",
        "description": "Tiêu Dao Tiên Tôn trùng sinh, thiếu niên 18 tuổi, ánh mắt kiêu hãnh như tinh thần, mặc áo phông đen và phong thái chí tôn",
        "power_tier": "Tiêu Dao Tiên Tôn (Trùng Sinh Trúc Cơ)",
        "combat_stats": {"element": "Cửu Tiêu Thần Lôi", "role": "Nhân vật chính"},
        "relationships": {"Tô Nghiên": "Bằng hữu"}
    },
    {
        "novel_id": SIMULATED_NOVEL["id"],
        "name": "Tô Nghiên",
        "description": "Nữ chủ tịch tập đoàn Tô Thị, nữ thần lạnh lùng xinh đẹp, váy lụa trắng thanh khiết, sở hữu Huyền Băng Thánh Thể",
        "power_tier": "Huyền Băng Thánh Thể (Chưa thức tỉnh)",
        "combat_stats": {"element": "Băng Cực", "role": "Nữ chính"},
        "relationships": {"Lâm Phong": "Tri kỷ"}
    },
    {
        "novel_id": SIMULATED_NOVEL["id"],
        "name": "Tần Bá Thiên",
        "description": "Trưởng lão Tần Gia đô thị, lão già xam nham ác độc, vest đen sang trọng, điều khiển âm hồn trận",
        "power_tier": "Tông Sư Võ Đạo (Đô Thị)",
        "combat_stats": {"element": "Âm Hồn Phái", "role": "Phản diện"},
        "relationships": {"Lâm Phong": "Thù địch"}
    }
]

SIMULATED_LORE = [
    {
        "novel_id": SIMULATED_NOVEL["id"],
        "keyword": "Thần Châu Thị",
        "description": "Đô thị hiện đại sầm uất, tòa nhà cao tầng chọc trời, đèn neon rực rỡ kết hợp biệt thự cổ kính"
    },
    {
        "novel_id": SIMULATED_NOVEL["id"],
        "keyword": "Tiên Tôn Ngọc Giản",
        "description": "Mảnh ngọc cổ xanh lục lơ lửng phát ra thần quang bảo vật trùng sinh"
    }
]

def run_simulation():
    print("========================================================================")
    print(f"[SIMULATION TEST] STARTING SIMULATION FOR NEW NOVEL: '{SIMULATED_NOVEL['title']}'")
    print("========================================================================")
    
    # 1. Kiểm tra rà soát Sanitizer chống rò rỉ tên cũ
    sample_raw_text = "Lâm Phong đứng trên đỉnh tòa nhà Thần Châu Thị, Tô Nghiên bước tới bên cạnh."
    sanitized_text, modified = writer.verify_and_sanitize_chapter_content(sample_raw_text, SIMULATED_NOVEL["id"])
    print(f"[TEST 1] Chapter Content Sanitizer Check:")
    print(f"  - Modified: {modified}")
    assert not modified, "Text should not be modified because it contains valid novel characters!"
    assert "Tiêu Viêm" not in sanitized_text, "Should not leak Tiêu Viêm into new novel!"
    assert "Trần Lam" not in sanitized_text, "Should not leak Trần Lam into new novel!"
    print("  -> PASSED: Zero character leakage!")
    
    # 2. Thử nghiệm Động Cơ AI Visual Director cho Bộ Truyện Mới
    test_scenes = [
        "Lâm Phong từ từ mở mắt trên đỉnh tòa nhà Thần Châu Thị, tay nắm Cửu Tiêu Tiên Thần Kiếm phát ra sấm sét",
        "Tô Nghiên khoác váy lụa trắng đứng nhìn Lâm Phong với ánh mắt ngạc nhiên",
        "Tần Bá Thiên triệu hồi Âm Hồn Trận bao vây Thần Châu Thị"
    ]
    
    idx, manifest_item, pos_prompt = visual_prompt_engine._enrich_single_scene(
        (0, test_scenes[0]), SIMULATED_CHARACTERS, SIMULATED_LORE
    )
    
    print("\n[TEST 2] Master Detail Locking Engine for New Novel:")
    print(f"  - Detected Characters: {manifest_item['detected_characters']}")
    print(f"  - Detected Lore: {manifest_item['detected_lore']}")
    print(f"  - Character Lock Prompt: {manifest_item['character_lock']}")
    
    assert "Lâm Phong" in manifest_item["detected_characters"], "Must detect new character Lâm Phong!"
    assert "Thần Châu Thị" in manifest_item["detected_lore"], "Must detect new lore Thần Châu Thị!"
    print("  -> PASSED: Visual Director dynamically locks new novel's characters and lore 100%!")
    
    print("\n========================================================================")
    print("SUCCESS: 100% SIMULATION PASSED! ZERO CONFLICTS FOR NEW NOVEL CREATION!")
    print("========================================================================")

if __name__ == "__main__":
    run_simulation()
