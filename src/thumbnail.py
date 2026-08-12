import os
from PIL import Image, ImageDraw, ImageFont
from src.image_generator import generate_scene_image

def overlay_thumbnail_text(image_path: str, chapter_number: int, title: str) -> str:
    """Tự động chèn chữ tiêu đề YouTube High-CTR (Chữ Vàng/Trắng viền đen nổi bật) lên ảnh Thumbnail."""
    if not os.path.exists(image_path):
        return image_path
        
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        # Tạo lớp overlay mờ mịt ở phần dưới để làm nổi chữ
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Vẽ dải gradient / mảng tối phía dưới ảnh (Bottom Dark Gradient)
        bottom_box = [(0, int(height * 0.7)), (width, height)]
        draw.rectangle(bottom_box, fill=(0, 0, 0, 160))
        
        # Vẽ thẻ Badge góc trên (Top Badge)
        badge_box = [(40, 40), (min(520, width - 10), min(110, height // 8))]
        draw.rectangle(badge_box, fill=(220, 38, 38, 230)) # Màu đỏ nổi bật
        
        # Ghép overlay vào ảnh chính
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw_final = ImageDraw.Draw(img)
        
        # Thử nạp Font IMPACT Ultra-Bold (Phông chữ YouTube Thumbnail đẹp nhất thế giới) với fallback linh hoạt
        font_candidates = [
            "C:/Windows/Fonts/impact.ttf", "impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf"
        ]
        
        font_large = None
        font_badge = None
        for fpath in font_candidates:
            try:
                if os.path.exists(fpath):
                    font_large = ImageFont.truetype(fpath, 76)
                    font_badge = ImageFont.truetype(fpath, 42)
                    print(f"[INFO] Loaded Ultra-Bold Thumbnail Font: {fpath}")
                    break
            except Exception:
                continue
                
        if not font_large:
            font_large = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            
        # 1. Viết chữ Badge Top Thương Hiệu Chính Thức: 🔥 TRUYỆN 24H - SIÊU PHẨM
        draw_final.text((60, 52), "🔥 TRUYỆN 24H - SIÊU PHẨM", fill=(255, 255, 255), font=font_badge)
        
        # 2. Viết chữ Tiêu đề Tập & Tên chương (IMPACT Font + Viền đen 5px + Drop Shadow)
        chapter_str = f"TẬP {chapter_number}: {title.upper()}"
        text_x = 50
        text_y = int(height * 0.78)
        
        # A. Vẽ lớp bóng đổ đen phía sau (Drop Shadow Offset +3px)
        shadow_color = (0, 0, 0, 220)
        draw_final.text((text_x + 4, text_y + 4), chapter_str, fill=shadow_color, font=font_large)
        
        # B. Vẽ viền đen siêu dày 5px xung quanh chữ (Heavy 5px Stroke Outline)
        stroke_color = (0, 0, 0)
        for offset_x in range(-5, 6):
            for offset_y in range(-5, 6):
                draw_final.text((text_x + offset_x, text_y + offset_y), chapter_str, fill=stroke_color, font=font_large)
                
        # C. Vẽ chữ chính màu Vàng Hoàng Kim (Gold Accent #FFD700)
        draw_final.text((text_x, text_y), chapter_str, fill=(255, 215, 0), font=font_large)
        
        # Lưu lại đè lên file Thumbnail chất lượng 98%
        img.save(image_path, "JPEG", quality=98)
        print(f"[SUCCESS] Applied Impact Ultra-Bold Text Overlay to Thumbnail: {image_path}")
    except Exception as e:
        print(f"[WARNING] Could not apply text overlay to thumbnail: {e}")
        
    return image_path

def generate_youtube_thumbnail(title: str, chapter_number: int, output_path: str) -> str:
    """
    Feature 1 Nâng Cấp: Tự động tạo YouTube Thumbnail 4K High-CTR chuẩn ngách Truyện Manhwa Audio.
    Học tập các kênh triệu view: Khung hình 2D Manhwa 8K, thần thái nhân vật quyết đoán, hào quang năng lượng và Banner tiêu đề chữ nổi bật!
    """
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    
    # Prompt nghệ thuật đỉnh cao thiết kế riêng cho Thumbnail YouTube
    prompt = (
        f"masterpiece epic YouTube video thumbnail wallpaper, 2D manhwa webtoon style, "
        f"intense close-up hero portrait of handsome 18 years old young male cultivator, "
        f"glowing eyes, swirling cyan energy aura, floating glowing particles, "
        f"dramatic rim lighting, dark misty bamboo forest ruins background, "
        f"vivid color grading, high contrast, trending on ArtStation, 8k resolution, 16:9 aspect ratio"
    )
    
    # 1. Sinh ảnh AI 4K Manhwa
    bg_path = generate_scene_image(prompt, output_path, width=1920, height=1080)
    
    # 2. Chèn Banner chữ Tiêu Đề chuẩn YouTube High-CTR
    if bg_path and os.path.exists(bg_path):
        overlay_thumbnail_text(bg_path, chapter_number, title)
        
    return bg_path
