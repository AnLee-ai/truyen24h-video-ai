import os

with open(r'd:\222\src\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_logic = '''
        # Generate one unique badass base thumbnail per novel
        novel_base_thumb = os.path.join("output", novel_id, "base_thumbnail.jpg")
        if not os.path.exists(novel_base_thumb):
            print("[INFO] Tạo 1 ảnh Thumbnail gốc duy nhất siêu ngầu cho cả bộ truyện...")
            from src import image_generator
            prompt = "Masterpiece, best quality, 1boy, main character, badass, epic pose, glowing eyes, dark fantasy, highly detailed, 8k resolution, cinematic lighting, 16:9 wallpaper"
            try:
                image_generator.generate_image(prompt, novel_base_thumb, width=1920, height=1080, base_seed=12345)
            except Exception as e:
                print(f"[ERROR] Failed to generate base thumbnail: {e}")
                scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
                if os.path.exists(scene_img_p):
                    import shutil
                    shutil.copy(scene_img_p, novel_base_thumb)

        if not os.path.exists(novel_base_thumb):
             novel_base_thumb = os.path.join("output", chapter_id, "images", "scene_001.jpg")

        thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
        if os.path.exists(thumb_out_p):
            try:
                os.remove(thumb_out_p)
            except Exception as e:
                print(f"[ERROR] main.py: {e}")

        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num} (dùng base chung)...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, novel_base_thumb, thumb_out_p)
        if thumbnail_path and os.path.exists(thumbnail_path):
            database.upload_file_to_supabase(thumbnail_path, bucket_name="media", destination_path=f"thumbnails/{chapter_id}_thumbnail.jpg")
'''

lines[221:234] = [new_logic]

with open(r'd:\222\src\main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Patched correctly!')
