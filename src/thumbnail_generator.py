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
        
        # 1. Khởi tạo ảnh nền (Dùng ảnh phân cảnh AI nếu có, nếu không thì dùng gradient)
        if os.path.exists(scene_image_path) and os.path.getsize(scene_image_path) > 1000:
            bg_img = Image.open(scene_image_path).convert('RGB')
            bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        else:
            bg_img = Image.new('RGB', (width, height), color=(16, 20, 36))
            
        # 2. Phủ lớp Radial Vignette & Dark Gradient Manhwa
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Gradient tối ở nửa dưới (bottom 55%) và dải trái để làm nổi chữ
        for y in range(int(height * 0.45), height):
            ratio = (y - height * 0.45) / (height * 0.55)
            alpha = int(240 * (ratio ** 1.2))
            overlay_draw.line([(0, y), (width, y)], fill=(8, 10, 20, alpha))
            
        for x in range(0, int(width * 0.45)):
            ratio = (width * 0.45 - x) / (width * 0.45)
            alpha = int(190 * (ratio ** 1.2))
            overlay_draw.line([(x, 0), (x, height)], fill=(8, 10, 20, alpha))
            
        bg_img = Image.alpha_composite(bg_img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(bg_img)
        
        # 3. Phông chữ (Font System Fallback)
        def load_font(size):
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/tahomabd.ttf",
                "C:/Windows/Fonts/seguiemb.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
            for p in font_paths:
                if os.path.exists(p):
                    try:
                        return ImageFont.truetype(p, size)
                    except Exception:
                        pass
            return ImageFont.load_default()
            
        badge_font = load_font(50)
        tag_font = load_font(36)
        title_font = load_font(64)
        brand_font = load_font(42)
        
        # 4. Vẽ Huy hiệu 1: '🔥 TẬP X - BÁ CHỦ TRÙNG SINH' ở góc trái trên
        badge_text = f" 🔥 TẬP {chapter_num} - BÁ CHỦ TRÙNG SINH "
        badge_box = badge_font.getbbox(badge_text)
        bw = badge_box[2] - badge_box[0] + 36
        bh = badge_box[3] - badge_box[1] + 24
        
        bx, by = 70, 70
        # Viền mạ vàng 4px
        draw.rectangle([bx-5, by-5, bx + bw + 5, by + bh + 5], fill=(255, 215, 0))
        # Nền đỏ ma thuật mờ mượt
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(210, 18, 52))
        # Chữ trắng nổi bật
        draw.text((bx + 18, by + 10), badge_text, fill=(255, 255, 255), font=badge_font)

        # 4b. Vẽ Huy hiệu 2: '4K ULTRA HD' ở góc phải trên
        tag_text = " 4K ULTRA HD "
        tag_box = tag_font.getbbox(tag_text)
        tw = tag_box[2] - tag_box[0] + 24
        th = tag_box[3] - tag_box[1] + 16
        tx_tag, ty_tag = width - tw - 70, 70
        draw.rectangle([tx_tag-3, ty_tag-3, tx_tag + tw + 3, ty_tag + th + 3], fill=(0, 230, 118))
        draw.rectangle([tx_tag, ty_tag, tx_tag + tw, ty_tag + th], fill=(12, 28, 20))
        draw.text((tx_tag + 12, ty_tag + 6), tag_text, fill=(0, 230, 118), font=tag_font)

        # 5. Vẽ Tiêu Đề Chương (Chapter Title) Chữ Vàng 3D cực kỳ quyến rũ
        clean_title = re.sub(r"[^\w\s\-\:]", "", chapter_title)
        if len(clean_title) > 36:
            clean_title = clean_title[:34] + "..."
            
        title_text = f"Chương {chapter_num}: {clean_title}"
        tx, ty = 80, height - 220
        
        # Đổ bóng đen 3D siêu dày 5px (3D Shadow Outline)
        for offset_x, offset_y in [(-4,-4), (4,-4), (-4,4), (4,4), (-5,0), (5,0), (0,-5), (0,5), (-3,-3), (3,3)]:
            draw.text((tx + offset_x, ty + offset_y), title_text, fill=(0, 0, 0), font=title_font)
            
        # Chữ Vàng Hoàng Kim Tương Phản Cao
        draw.text((tx, ty), title_text, fill=(255, 223, 0), font=title_font)
        
        # 6. Vẽ Brand Watermark 'TRUYỆN 24H AUDIO STUDIO' góc dưới phải
        brand_text = "TRUYỆN 24H AUDIO STUDIO"
        bbox = brand_font.getbbox(brand_text)
        rx = width - (bbox[2] - bbox[0]) - 80
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
