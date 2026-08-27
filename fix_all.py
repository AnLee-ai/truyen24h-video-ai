import os, re

# 1. Update thumbnail_generator.py
thumb_file = r'd:\222\src\thumbnail_generator.py'
with open(thumb_file, 'r', encoding='utf-8') as f:
    t_content = f.read()

# Remove 4K ULTRA HD
t_content = re.sub(r"tag_text = . 4K ULTRA HD .*?tag_font\)", "", t_content, flags=re.DOTALL)

# Make AI NOVEL STUDIO bigger
t_content = t_content.replace("brand_font = load_font(42)", "brand_font = load_font(60)")

# 2. Update video.py for subtitle style and fallback image
video_file = r'd:\222\src\video.py'
with open(video_file, 'r', encoding='utf-8') as f:
    v_content = f.read()

new_subtitle_style = "Fontname=Arial,FontSize=24,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BackColour=&H00000000&,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=25,MarginL=60,MarginR=60,WrapStyle=2"

# Replace the old subtitle_style
v_content = re.sub(r'subtitle_style\s*=\s*".*?"', f'subtitle_style = "{new_subtitle_style}"', v_content)

# 3. Update main.py to use a fixed thumbnail per novel
main_file = r'd:\222\src\main.py'
with open(main_file, 'r', encoding='utf-8') as f:
    m_content = f.read()

thumbnail_logic_old = '''
        scene_img_p = os.path.join("output", chapter_id, "images", "scene_001.jpg")
        thumb_out_p = os.path.join("output", chapter_id, "thumbnail.jpg")
        if os.path.exists(thumb_out_p):
            try:
                os.remove(thumb_out_p)
            except Exception:
                pass
        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num}...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, scene_img_p, thumb_out_p)
'''

thumbnail_logic_new = '''
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
                # Fallback to scene_001 if generation fails
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
            except Exception:
                pass
        print(f"[INFO] Bắt đầu tự động thiết kế Thumbnail YouTube 16:9 cho Tập {chapter_num} (dùng base chung)...")
        thumbnail_path = thumbnail_generator.generate_youtube_thumbnail(chapter_num, chapter_title, novel_base_thumb, thumb_out_p)
'''

m_content = m_content.replace(thumbnail_logic_old.strip('\n'), thumbnail_logic_new.strip('\n'))

with open(thumb_file, 'w', encoding='utf-8') as f: f.write(t_content)
with open(video_file, 'w', encoding='utf-8') as f: f.write(v_content)
with open(main_file, 'w', encoding='utf-8') as f: f.write(m_content)
print("Updated successfully")
