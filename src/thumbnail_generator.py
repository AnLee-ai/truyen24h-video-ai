import os
import re
from PIL import Image, ImageDraw, ImageFont

def generate_youtube_thumbnail(chapter_num: int, chapter_title: str, scene_image_path: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Tự động thiết kế Ảnh Bìa Thumbnail YouTube (16:9 1920x1080) chuẩn MoneyPrinterTurbo / ComfyUI:
    - Nền: Bức ảnh phân cảnh AI rực rỡ + Phủ lớp Radial Vignette Manhwa 2D.
    - Huy hiệu 1: '🔥 TẬP X - BÁ CHỦ TRÙNG SINH' Nền Đỏ Ma Thuật, Viền Mạ Vàng góc trái trên.
    - Huy hiệu 2: '4K ULTRA HD' Nền Xanh Ngọc Emerald góc phải trên.
    - Tiêu đề: Chữ Vàng 64px Tương Phản Cao, Bóng Đen 3D 5px chống chói 100%.
    - Watermark: Logo 'TRUYỆN 24H AUDIO STUDIO' mạ xanh kim ở góc dưới.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 1. Khởi tạo ảnh nền (Load ảnh phân cảnh AI, tìm ảnh thay thế rộng hơn hoặc sinh ảnh AI/Canvas 16:9 HD)
        bg_loaded = False
        
        # A. Thử nạp trực tiếp scene_image_path
        if os.path.exists(scene_image_path) and os.path.getsize(scene_image_path) > 1000:
            try:
                bg_img = Image.open(scene_image_path).convert('RGB')
                bg_loaded = True
            except Exception:
                pass

        # B. Tìm ảnh thay thế trong cùng thư mục images/ hoặc các thư mục con trong output/
        if not bg_loaded:
            search_dirs = [
                os.path.dirname(scene_image_path),
                "output",
                "."
            ]
            for s_dir in search_dirs:
                if os.path.exists(s_dir):
                    try:
                        for root, _, files in os.walk(s_dir):
                            candidates = [
                                os.path.join(root, f) for f in files 
                                if f.lower().endswith(('.jpg', '.png', '.jpeg')) 
                                and os.path.getsize(os.path.join(root, f)) > 5000
                                and "thumbnail" not in f.lower()
                            ]
                            if candidates:
                                bg_img = Image.open(candidates[0]).convert('RGB')
                                bg_loaded = True
                                print(f"[INFO] 🖼️ Thumbnail dùng ảnh thay thế đạt chuẩn: {candidates[0]}")
                                break
                    except Exception:
                        pass
                if bg_loaded:
                    break

        # C. Tự động sinh ảnh AI 16:9 HD mới dành riêng cho Thumbnail Nhân Vật Chính Siêu Ngầu
        if not bg_loaded:
            try:
                from src.image_generator import generate_scene_image
                prompt_tb = (
                    f"masterpiece epic 2D anime manhwa webtoon illustration, {chapter_title}, "
                    f"ultra cool badass 18yo male cultivator hero portrait (Tiêu Viêm / Xiao Yan), "
                    f"intense fierce posture, glowing cyan eyes, spiky black hair blown by storm wind, "
                    f"holding glowing violet flaming sword, swirling cyan energy aura, floating particles, "
                    f"dramatic rim lighting, dark misty bamboo mountain background, trending on ArtStation, 8k resolution, 16:9"
                )
                gen_p = generate_scene_image(prompt_tb, scene_image_path, width, height)
                if gen_p and os.path.exists(gen_p) and os.path.getsize(gen_p) > 1000:
                    bg_img = Image.open(gen_p).convert('RGB')
                    bg_loaded = True
                    print(f"[INFO] 🎨 Tự động sinh ảnh AI Nhân Vật Chính Siêu Ngầu cho Thumbnail: {gen_p}")
            except Exception as gen_err:
                print(f"[WARNING] Không thể tự động sinh ảnh nền thumbnail: {gen_err}")

        # D. Fallback tuyệt đối: Vẽ bức canvas nghệ thuật 2D Xianxia Anime HD khắc họa Nhân Vật Chính Siêu Ngầu
        if not bg_loaded:
            print("[INFO] 🎨 Tạo bức Canvas nghệ thuật 2D Xianxia Anime HD với Nhân Vật Chính Siêu Ngầu...")
            import hashlib
            bg_img = Image.new('RGB', (width, height), color=(20, 25, 45))
            canvas_draw = ImageDraw.Draw(bg_img)
            
            # Gradient bầu trời đêm Xianxia rực rỡ (Deep Royal Purple -> Cyan Celestial -> Sunset Magenta)
            for y in range(height):
                ratio = y / height
                r = int(60 * (1 - ratio) + 20 * ratio)
                g = int(25 * (1 - ratio) + 120 * ratio)
                b = int(110 * (1 - ratio) + 210 * ratio)
                canvas_draw.line([(0, y), (width, y)], fill=(r, g, b))
                
            # Tia sáng hào quang năng lượng tỏa ra từ tâm (Celestial God Rays)
            cx, cy = width * 3 // 4, height // 3
            for angle in range(0, 360, 15):
                import math
                rad = math.radians(angle)
                end_x = cx + int(800 * math.cos(rad))
                end_y = cy + int(800 * math.sin(rad))
                canvas_draw.line([(cx, cy), (end_x, end_y)], fill=(80, 180, 240), width=3)
                
            # Ngôi sao & hạt linh khí lơ lửng lung linh
            seed_val = int(hashlib.md5(chapter_title.encode('utf-8')).hexdigest()[:6], 16)
            for i in range(150):
                sx = (seed_val * (i + 1) * 37) % width
                sy = (seed_val * (i + 1) * 73) % (height * 4 // 5)
                s_size = (i % 4) + 1
                canvas_draw.ellipse([sx, sy, sx + s_size, sy + s_size], fill=(255, 255, 230))
                
            # Mặt trăng / Quầng sáng linh khí (Xianxia Celestial Energy Core)
            for radius in range(280, 40, -20):
                alpha_c = int(50 * (1 - radius / 280))
                canvas_draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(40 + alpha_c, 160 + alpha_c, 230 + alpha_c))
            canvas_draw.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(255, 248, 220))
            
            # Dãy núi tiên cảnh trùng điệp phía dưới
            points1 = [(0, height)]
            for x in range(0, width + 60, 60):
                hy = height * 3 // 5 - (int(hashlib.md5(f"m1_{x}".encode()).hexdigest()[:4], 16) % 180)
                points1.append((x, hy))
            points1.append((width, height))
            canvas_draw.polygon(points1, fill=(25, 45, 85))
            
            points2 = [(0, height)]
            for x in range(0, width + 50, 50):
                hy = height * 3 // 4 - (int(hashlib.md5(f"m2_{x}".encode()).hexdigest()[:4], 16) % 140)
                points2.append((x, hy))
            points2.append((width, height))
            canvas_draw.polygon(points2, fill=(15, 25, 50))

            # Bổ sung: Nhân vật chính (Hero Cultivator Silhouette) đứng trên đỉnh núi giơ cao Hỏa Kiếm Siêu Ngầu
            hx, hy = width // 3, height * 2 // 3
            # Hào quang thần thái bao quanh nhân vật chính
            for r_aura in range(120, 20, -15):
                canvas_draw.ellipse([hx - r_aura, hy - r_aura - 80, hx + r_aura, hy + r_aura - 80], fill=(255, 215, 0, 40))
            # Hỏa kiếm hoàng kim giơ cao
            canvas_draw.line([(hx, hy - 40), (hx + 60, hy - 220)], fill=(255, 223, 0), width=8)
            canvas_draw.line([(hx, hy - 40), (hx + 60, hy - 220)], fill=(255, 255, 255), width=3)
            # Bóng nhân vật nam chính vai rộng tóc nhọn ngầu
            canvas_draw.ellipse([hx - 25, hy - 140, hx + 25, hy - 90], fill=(12, 16, 28))  # Đầu & tóc
            canvas_draw.polygon([(hx - 50, hy), (hx + 50, hy), (hx + 30, hy - 90), (hx - 30, hy - 90)], fill=(12, 16, 28))  # Thân áo trường bào

        bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
            
        # 2. Phủ lớp Radial Vignette & Dark Gradient Manhwa (Cân bằng độ trong suốt để ảnh nền rực rỡ)
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for y in range(int(height * 0.55), height):
            ratio = (y - height * 0.55) / (height * 0.45)
            alpha = int(90 * (ratio ** 1.2))
            overlay_draw.line([(0, y), (width, y)], fill=(8, 10, 20, alpha))
            
        for x in range(0, int(width * 0.35)):
            ratio = (width * 0.35 - x) / (width * 0.35)
            alpha = int(70 * (ratio ** 1.2))
            overlay_draw.line([(x, 0), (x, height)], fill=(8, 10, 20, alpha))
            
        bg_img = Image.alpha_composite(bg_img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(bg_img)
        
        # 3. Phông chữ (Font System Fallback - Hỗ trợ cả Windows và Linux/Docker Container)
        def load_font(size):
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/tahomabd.ttf",
                "C:/Windows/Fonts/seguiemb.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
            for p in font_paths:
                if os.path.exists(p):
                    try:
                        return ImageFont.truetype(p, size)
                    except Exception:
                        pass
            try:
                return ImageFont.truetype("arial.ttf", size)
            except Exception:
                return ImageFont.load_default()
            
        def get_safe_text_size(font_obj, text_str, char_w=22, char_h=40):
            try:
                bbox = font_obj.getbbox(text_str)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if 10 <= w <= 1800 and 10 <= h <= 300:
                    return w, h
            except Exception:
                pass
            return len(text_str) * char_w, char_h

        badge_font = load_font(50)
        tag_font = load_font(36)
        title_font = load_font(64)
        brand_font = load_font(42)
        
        # 4. Vẽ Huy hiệu 1: '🔥 TẬP X - BÁ CHỦ TRÙNG SINH' ở góc trái trên
        badge_text = f" 🔥 TẬP {chapter_num} - BÁ CHỦ TRÙNG SINH "
        bw_text, bh_text = get_safe_text_size(badge_font, badge_text, 22, 45)
        bw = min(max(bw_text + 36, 250), 700)
        bh = min(max(bh_text + 24, 50), 100)
        
        bx, by = 70, 70
        # Viền mạ vàng 4px
        draw.rectangle([bx-5, by-5, bx + bw + 5, by + bh + 5], fill=(255, 215, 0))
        # Nền đỏ ma thuật mờ mượt
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(210, 18, 52))
        # Chữ trắng nổi bật
        draw.text((bx + 18, by + 10), badge_text, fill=(255, 255, 255), font=badge_font)

        # 4b. Vẽ Huy hiệu 2: '4K ULTRA HD' ở góc phải trên (Giới hạn kích thước thẻ an toàn chống lỗi viền xanh)
        tag_text = " 4K ULTRA HD "
        tw_text, th_text = get_safe_text_size(tag_font, tag_text, 18, 35)
        tw = min(max(tw_text + 24, 160), 280)
        th = min(max(th_text + 16, 40), 70)
        tx_tag = width - tw - 70
        ty_tag = 70
        draw.rectangle([tx_tag-3, ty_tag-3, tx_tag + tw + 3, ty_tag + th + 3], fill=(0, 230, 118))
        draw.rectangle([tx_tag, ty_tag, tx_tag + tw, ty_tag + th], fill=(12, 28, 20))
        draw.text((tx_tag + 12, ty_tag + 6), tag_text, fill=(0, 230, 118), font=tag_font)

        # 5. Vẽ Tiêu Đề Chương (Chapter Title) Chữ Vàng 3D cực kỳ quyến rũ
        clean_title = re.sub(r"[^\w\s\-\:]", "", chapter_title)
        if len(clean_title) > 36:
            short_t = clean_title[:34]
            if " " in short_t:
                short_t = short_t.rsplit(" ", 1)[0]
            clean_title = short_t + "..."
            
        title_text = f"Chương {chapter_num}: {clean_title}"
        tx, ty = 80, height - 220
        
        # Đổ bóng đen 3D siêu dày 5px (3D Shadow Outline)
        for offset_x, offset_y in [(-4,-4), (4,-4), (-4,4), (4,4), (-5,0), (5,0), (0,-5), (0,5), (-3,-3), (3,3)]:
            draw.text((tx + offset_x, ty + offset_y), title_text, fill=(0, 0, 0), font=title_font)
            
        # Chữ Vàng Hoàng Kim Tương Phản Cao
        draw.text((tx, ty), title_text, fill=(255, 223, 0), font=title_font)
        
        # 6. Vẽ Brand Watermark 'TRUYỆN 24H AUDIO STUDIO' góc dưới phải
        brand_text = "TRUYỆN 24H AUDIO STUDIO"
        br_w, _ = get_safe_text_size(brand_font, brand_text, 20, 40)
        br_w = min(max(br_w, 300), 700)
        rx = width - br_w - 80
        ry = height - 100
        
        for ox, oy in [(-3,-3), (3,-3), (-3,3), (3,3)]:
            draw.text((rx + ox, ry + oy), brand_text, fill=(0, 0, 0), font=brand_font)
        draw.text((rx, ry), brand_text, fill=(0, 230, 118), font=brand_font)
        
        bg_img.save(output_path, quality=95)
        print(f"[SUCCESS] Generated 16:9 MoneyPrinter/ComfyUI YouTube Thumbnail at: {output_path}")
        return output_path
    except Exception as e:
        print(f"[WARNING] Thumbnail generation failed: {e}")
        return ""
