import os
import re
from PIL import Image, ImageDraw, ImageFont

def generate_youtube_thumbnail(chapter_num: int, chapter_title: str, scene_image_path: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Tự động thiết kế Ảnh Bìa Thumbnail YouTube (16:9 1920x1080) siêu bắt mắt:
    - Nền: Bức ảnh phân cảnh AI rực rỡ + Phủ lớp Gradient vệt tối Manhwa 2D.
    - Huy hiệu: 'TẬP X' khung đỏ mạ vàng góc trên.
    - Tiêu đề: Chữ Vàng 52px bóng đen 3D chống chói.
    - Watermark: Logo 'TRUYỆN 24H' mạ vàng ở góc dưới.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 1. Khởi tạo ảnh nền (Dùng ảnh phân cảnh AI nếu có, nếu không thì dùng gradient)
        if os.path.exists(scene_image_path) and os.path.getsize(scene_image_path) > 1000:
            bg_img = Image.open(scene_image_path).convert('RGB')
            bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        else:
            bg_img = Image.new('RGB', (width, height), color=(20, 24, 40))
            
        draw = ImageDraw.Draw(bg_img)
        
        # 2. Phủ lớp vệt tối Manhwa (Dark Vignette & Shadow Overlay)
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Gradient tối ở dải dưới và dải trái để nổi chữ
        for y in range(int(height * 0.4), height):
            alpha = int(220 * ((y - height * 0.4) / (height * 0.6)))
            overlay_draw.line([(0, y), (width, y)], fill=(10, 10, 18, alpha))
            
        for x in range(0, int(width * 0.4)):
            alpha = int(180 * ((width * 0.4 - x) / (width * 0.4)))
            overlay_draw.line([(x, 0), (x, height)], fill=(10, 10, 18, alpha))
            
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
            
        badge_font = load_font(46)
        title_font = load_font(56)
        brand_font = load_font(38)
        
        # 4. Vẽ Huy hiệu 'TẬP X' (Red & Gold Episode Badge) ở góc trái trên
        badge_text = f" TẬP {chapter_num} "
        badge_box = badge_font.getbbox(badge_text)
        bw = badge_box[2] - badge_box[0] + 30
        bh = badge_box[3] - badge_box[1] + 20
        
        bx, by = 60, 60
        # Viền mạ vàng
        draw.rectangle([bx-4, by-4, bx + bw + 4, by + bh + 4], fill=(255, 215, 0))
        # Nền đỏ ma thuật
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(220, 20, 60))
        # Chữ trắng
        draw.text((bx + 15, by + 8), badge_text, fill=(255, 255, 255), font=badge_font)
        
        # 5. Vẽ Tiêu Đề Chương (Chapter Title) Chữ Vàng nổi 3D ở góc dưới trái
        clean_title = re.sub(r"[^\w\s\-\:]", "", chapter_title)
        if len(clean_title) > 40:
            clean_title = clean_title[:38] + "..."
            
        title_text = f"Tập {chapter_num}: {clean_title}"
        tx, ty = 70, height - 200
        
        # Bóng đen 3D (Shadow Outline)
        for offset_x, offset_y in [(-3,-3), (3,-3), (-3,3), (3,3), (-4,0), (4,0), (0,-4), (0,4)]:
            draw.text((tx + offset_x, ty + offset_y), title_text, fill=(0, 0, 0), font=title_font)
            
        # Chữ Vàng Hoàng Kim
        draw.text((tx, ty), title_text, fill=(255, 223, 0), font=title_font)
        
        # 6. Vẽ Brand Watermark 'TRUYỆN 24H' ở góc dưới phải
        brand_text = "TRUYỆN 24H AUDIO STUDIO"
        bbox = brand_font.getbbox(brand_text)
        rx = width - (bbox[2] - bbox[0]) - 80
        ry = height - 100
        
        # Viền đen
        for ox, oy in [(-2,-2), (2,-2), (-2,2), (2,2)]:
            draw.text((rx + ox, ry + oy), brand_text, fill=(0, 0, 0), font=brand_font)
        draw.text((rx, ry), brand_text, fill=(0, 230, 118), font=brand_font)
        
        bg_img.save(output_path, quality=95)
        print(f"[SUCCESS] Generated 16:9 YouTube Thumbnail at: {output_path}")
        return output_path
    except Exception as e:
        print(f"[WARNING] Thumbnail generation failed: {e}")
        return ""
