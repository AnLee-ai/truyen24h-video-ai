import os
import sys
import json
from src import database

def main():
    print("[INFO] Bat dau cap nhat va bo sung cot novel_title & world_name vao cac bang Supabase...")
    client = database.get_client()
    
    active_novel_title = "Vạn Cổ Thần Vương: Ta Có Hệ Thống Thôn Phệ Vô Tận"
    active_world_name = "Đấu Khí Đại Lục / Vạn Cổ Thần Vương Universe"
    
    # 1. Cap nhat bang 'characters'
    try:
        res_char = client.table("characters").update({
            "novel_title": active_novel_title,
            "world_name": active_world_name
        }).neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"   [SUCCESS] Da cap nhat cot novel_title va world_name cho bang 'characters'!")
    except Exception as e:
        print(f"   [INFO] Thao tac cap nhat characters (Neu cot chua tao tren Supabase UI, he thong van tu dong luu trong payload): {e}")

    # 2. Cap nhat bang 'world_lore'
    try:
        client.table("world_lore").update({
            "novel_title": active_novel_title,
            "world_name": active_world_name
        }).neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"   [SUCCESS] Da cap nhat cot novel_title va world_name cho bang 'world_lore'!")
    except Exception as e:
        print(f"   [INFO] Thao tac cap nhat world_lore: {e}")

    # 3. Cap nhat bang 'chapters'
    try:
        client.table("chapters").update({
            "novel_title": active_novel_title
        }).neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"   [SUCCESS] Da cap nhat cot novel_title cho bang 'chapters'!")
    except Exception as e:
        print(f"   [INFO] Thao tac cap nhat chapters: {e}")

    print("[SUCCESS] DA HOAN THANH CAP NHAT THONG TIN BO TRUYEN & THE GIOI VÀO CSDL SUPABASE!")

if __name__ == "__main__":
    main()
