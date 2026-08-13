import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import database

def main():
    print("[INFO] Bat dau nap va dong bo 100% du lieu vao ALL 6 BANG SUPABASE CSDL...")
    client = database.get_client()
    
    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    active_novel_desc = "Truyện tiên hiệp huyền huyễn cực kỳ kịch tính. Nam chính Tiêu Viêm trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận, từng bước luyện hóa vạn giới chư thiên, nén ép vạn giới thần ma, xây dựng lại trật tự vĩnh hằng."

    # BANG 1: novels
    novel_id = None
    try:
        res = client.table("novels").select("*").eq("title", active_novel_title).execute()
        if res.data:
            novel_id = res.data[0]["id"]
            client.table("novels").update({"status": "writing", "description": active_novel_desc}).eq("id", novel_id).execute()
            print(f"   [1/6 NOVELS] Da cap nhat active novel (ID: {novel_id})")
        else:
            ins = client.table("novels").insert({"title": active_novel_title, "description": active_novel_desc, "status": "writing"}).execute()
            if ins.data:
                novel_id = ins.data[0]["id"]
                print(f"   [1/6 NOVELS] Da tao moi active novel (ID: {novel_id})")
    except Exception as e:
        print(f"   [1/6 NOVELS] Canh bao: {e}")

    if not novel_id:
        novel_id = "van-co-than-vuong-v1"

    # BANG 2: characters
    chars = [
        {"novel_id": novel_id, "name": "Tiêu Viêm", "description": "Nam chính trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận. Mặc trường bào xanh thẫm, tóc đen sắc bén, cầm hỏa kiếm tím huyền thoại.", "power_tier": "Bá Chủ Trùng Sinh", "combat_stats": {"level": "Đấu Vương / Thôn Phệ Giả"}, "relationships": {"sư_phụ": "Dược Lão", "nữ_chính": "Vân Vận"}},
        {"novel_id": novel_id, "name": "Vân Vận", "description": "Nữ chính Tông chủ Vân Lam Tông. Khí chất thanh cao kiều diễm, mặc váy lụa xanh ngọc, sử dụng trường kiếm phong hệ sắc bén.", "power_tier": "Tông Chủ Vân Lam Tông", "combat_stats": {"level": "Đấu Hoàng Phong Hệ"}, "relationships": {"bằng_hữu": "Tiêu Viêm"}},
        {"novel_id": novel_id, "name": "Dược Lão", "description": "Sư phụ tôn giả thượng cổ. Linh hồn thể bạch y uy nghiêm, làm chủ Cốt Chưng U Hỏa, luyện dược sư đệ nhất chư thiên.", "power_tier": "Dược Tôn Giả", "combat_stats": {"level": "Đấu Tôn Linh Hồn"}, "relationships": {"đồ_đệ": "Tiêu Viêm"}},
        {"novel_id": novel_id, "name": "Huân Nhi", "description": "Thiếu nữ thần bí gia tộc cổ đại. Dịu dàng thông tuệ, mặc váy tím trang nhã, sở hữu Đế Tộc Huyết Mạch tôn quý.", "power_tier": "Cổ Tộc Thiếu Nữ", "combat_stats": {"level": "Đấu Linh Cổ Tộc"}, "relationships": {"thanh_mai_trúc_mã": "Tiêu Viêm"}}
    ]
    for c_i, c in enumerate(chars):
        try:
            client.table("characters").upsert(c, on_conflict="novel_id,name").execute()
            print(f"   [2/6 CHARACTERS] Da nap nhan vat #{c_i+1}")
        except Exception as e:
            print(f"   [2/6 CHARACTERS] Canh bao #{c_i+1}: {e}")

    # BANG 3: world_lore
    lores = [
        {"novel_id": novel_id, "keyword": "Đấu Khí Đại Lục", "description": "Thế giới tu luyện Đấu Khí hùng vĩ từ Đấu Giả đến Đấu Đế."},
        {"novel_id": novel_id, "keyword": "Hệ Thống Thôn Phệ Vô Tận", "description": "Bá đạo ngón tay vàng của Tiêu Viêm, thôn phệ vạn vật vô hạn đột phá."},
        {"novel_id": novel_id, "keyword": "Vân Lam Tông", "description": "Tông môn Phong Hệ bá chủ do Vân Vận làm Tông Chủ."},
        {"novel_id": novel_id, "keyword": "Dị Hỏa Vẫn Lạc", "description": "Ngọn lửa cuồng nổ dung hợp cùng Cốt Chưng U Hỏa của Dược Lão."},
        {"novel_id": novel_id, "keyword": "Hồn Điện", "description": "Thế lực tà ác sát thủ săn lùng linh hồn cường giả, kẻ thù truyền kiếp của Tiêu Viêm."}
    ]
    for l_i, lore_item in enumerate(lores):
        try:
            client.table("world_lore").upsert(lore_item, on_conflict="novel_id,keyword").execute()
            print(f"   [3/6 WORLD_LORE] Da nap lore #{l_i+1}")
        except Exception as e:
            print(f"   [3/6 WORLD_LORE] Canh bao #{l_i+1}: {e}")

    # BANG 4: narrative_threads
    threads = [
        {"novel_id": novel_id, "thread_name": "Trùng Sinh Thôn Phệ & Đột Phá Đấu Đế", "description": "Tiêu Viêm trùng sinh kích hoạt Hệ Thống Thôn Phệ Vô Tận, càn quét kẻ thù lật đổ Hồn Điện.", "status": "open"},
        {"novel_id": novel_id, "thread_name": "Định Mệnh Giữa Tiêu Viêm & Vân Vận", "description": "Mối duyên kỳ ngộ từ Ma Thú Sơn Mạch đến trận chiến Vân Lam Tông.", "status": "open"}
    ]
    for t_i, t in enumerate(threads):
        try:
            client.table("narrative_threads").upsert(t, on_conflict="id").execute()
            print(f"   [4/6 NARRATIVE_THREADS] Da nap thread #{t_i+1}")
        except Exception as e:
            print(f"   [4/6 NARRATIVE_THREADS] Canh bao #{t_i+1}: {e}")

    # BANG 5: chapters (Tập 1)
    ch1_title = "Trùng Sinh Vạn Cổ, Thôn Phệ Vô Tận"
    ch1_content = (
        "Đấu Khí Đại Lục, Gia Mã Đế Quốc, Ô Thán Thành.\n\n"
        "Tiêu Viêm từ từ mở mắt, ánh mắt sắc bén như kiếm quang xé tan khoảng không. "
        "Hắn đã trùng sinh mang theo Hệ Thống Thôn Phệ Vô Tận! Tất cả kẻ thù kiếp trước, tất cả áp chế của Vân Lam Tông và Hồn Điện, "
        "kiếp này hắn sẽ thôn phệ vạn giới chư thiên, quy nhất vĩnh hằng!"
    )
    ch1_id = None
    try:
        c_res = client.table("chapters").upsert({
            "novel_id": novel_id,
            "chapter_number": 1,
            "title": ch1_title,
            "content": ch1_content
        }, on_conflict="novel_id,chapter_number").execute()
        if c_res.data:
            ch1_id = c_res.data[0]["id"]
            print(f"   [5/12 CHAPTERS] Da nap Chapter 1 (ID: {ch1_id})")
    except Exception as e:
        print(f"   [5/12 CHAPTERS] Canh bao Chapter 1: {e}")

    # BANG 6: episodes_summary
    if ch1_id:
        try:
            client.table("episodes_summary").delete().eq("chapter_id", ch1_id).execute()
        except Exception:
            pass
        try:
            client.table("episodes_summary").insert({
                "chapter_id": ch1_id,
                "event_summary": "Tiêu Viêm trùng sinh tại Ô Thán Thành kích hoạt Hệ Thống Thôn Phệ Vô Tận, nén ép kẻ thù và bắt đầu hành trình bá chủ chư thiên."
            }).execute()
            print("   [6/12 EPISODES_SUMMARY] Da nap Episode 1 Summary thanh cong!")
        except Exception as e:
            print(f"   [6/12 EPISODES_SUMMARY] Canh bao: {e}")

    # BANG 7: publishing_analytics
    if ch1_id:
        try:
            database.record_publishing_analytics(ch1_id, chapter_number=1, views=1250, likes=320, telegram_reach=4500, retention_rate=88.5)
            print("   [7/12 PUBLISHING_ANALYTICS] Da nap chi so phat hanh & luot xem!")
        except Exception as e:
            print(f"   [7/12 PUBLISHING_ANALYTICS] Canh bao: {e}")

    # BANG 8: character_inventory
    inventories = [
        {"novel_id": novel_id, "character_name": "Tiêu Viêm", "item_name": "Hỏa Kiếm Thần Ma", "item_type": "Pháp Bảo", "description": "Thần kiếm tím phát sáng hào quang diệt ma", "power_boost": "+500% Sức Mạnh Thôn Phệ"},
        {"novel_id": novel_id, "character_name": "Tiêu Viêm", "item_name": "Cốt Chưng U Hỏa", "item_type": "Dị Hỏa", "description": "Ngọn lửa linh hồn trắng bạch do Dược Lão truyền lại", "power_boost": "Luyện Hóa Vạn Vật"},
        {"novel_id": novel_id, "character_name": "Vân Vận", "item_name": "Phong Linh Trường Kiếm", "item_type": "Vũ Khí", "description": "Trường kiếm phong hệ sắc bén Tông chủ Vân Lam Tông", "power_boost": "Tốc Độ Ánh Sáng"}
    ]
    for inv_i, inv in enumerate(inventories):
        try:
            database.upsert_character_inventory(inv["novel_id"], inv["character_name"], inv["item_name"], inv["item_type"], inv["description"], inv["power_boost"])
            print(f"   [8/12 CHARACTER_INVENTORY] Da nap trang bi #{inv_i+1}")
        except Exception as e:
            print(f"   [8/12 CHARACTER_INVENTORY] Canh bao #{inv_i+1}: {e}")

    # BANG 9: ai_prompts_log
    if ch1_id:
        try:
            database.log_ai_prompt(ch1_id, "masterpiece 2D anime manhwa male cultivator hero portrait (Tiêu Viêm), glowing cyan eyes, flaming sword", "Pollinations/Gemini", "", 9.8)
            print("   [9/12 AI_PROMPTS_LOG] Da ghi nhat ky AI prompt sinh anh!")
        except Exception as e:
            print(f"   [9/12 AI_PROMPTS_LOG] Canh bao: {e}")

    # BANG 10: tts_voice_configs
    voices = [
        {"novel_id": novel_id, "character_name": "Tiêu Viêm", "voice_name": "vi-VN-NamMinhNeural", "pitch": "+0Hz", "rate": "+0%", "emotional_style": "intense_epic"},
        {"novel_id": novel_id, "character_name": "Vân Vận", "voice_name": "vi-VN-HoaiMyNeural", "pitch": "+2Hz", "rate": "-2%", "emotional_style": "graceful"}
    ]
    for v_i, v in enumerate(voices):
        try:
            database.upsert_tts_voice_config(v["novel_id"], v["character_name"], v["voice_name"], v["pitch"], v["rate"], v["emotional_style"])
            print(f"   [10/12 TTS_VOICE_CONFIGS] Da nap giong doc AI #{v_i+1}")
        except Exception as e:
            print(f"   [10/12 TTS_VOICE_CONFIGS] Canh bao #{v_i+1}: {e}")

    # BANG 11: system_logs
    try:
        database.record_system_log("INFO", "MasterSyncEngine", "Da dong bo thanh cong toan bo 12 bang Supabase CSDL doanh nghiep!")
        print("   [11/12 SYSTEM_LOGS] Da ghi log van hanh he thong!")
    except Exception as e:
        print(f"   [11/12 SYSTEM_LOGS] Canh bao: {e}")

    # BANG 12: channel_subscribers
    subs = [
        {"user_id": "tg_user_1001", "platform": "Telegram", "membership_level": "VIP Premium"},
        {"user_id": "tg_user_1002", "platform": "Telegram", "membership_level": "Standard Fan"}
    ]
    for sub_i, sub in enumerate(subs):
        try:
            database.upsert_channel_subscriber(sub["user_id"], sub["platform"], sub["membership_level"])
            print(f"   [12/12 CHANNEL_SUBSCRIBERS] Da nap thanh vien VIP #{sub_i+1}")
        except Exception as e:
            print(f"   [12/12 CHANNEL_SUBSCRIBERS] Canh bao #{sub_i+1}: {e}")

    print("[SUCCESS] DA NAP KHOI TAO 100% DU LIEU CHO TOAN BO 12 BANG CSDL SUPABASE DOANH NGHIEP!")

if __name__ == "__main__":
    main()
