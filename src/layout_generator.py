import os
from PIL import Image, ImageDraw, ImageFont
import textwrap

def draw_speech_bubble(image_path: str, text: str, output_path: str) -> bool:
    """
    Tích hợp Mangstoon AI (CPU Mode): Vẽ bong bóng thoại chuẩn Manga/Webtoon lên ảnh AI.
    Rất nhẹ, chạy tốt trên i5 8GB RAM.
    """
    if not os.path.exists(image_path):
        return False

    try:
        with Image.open(image_path, encoding="utf-8") as img:
            img = img.convert("RGBA")
            width, height = img.size
            draw = ImageDraw.Draw(img)
            
            # Giả lập Mangstoon AI: Tính toán kích thước bong bóng thoại
            try:
                # Tìm font Arial hoặc font mặc định
                font = ImageFont.truetype("arial.ttf", size=int(height * 0.04))
            except IOError:
                font = ImageFont.load_default()

            # Bọc chữ (Wrap text)
            max_chars_per_line = 30
            wrapped_text = textwrap.fill(text, width=max_chars_per_line)
            
            # Tính toán Bounding Box (Mới trong Pillow >= 8.0.0)
            bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            padding = 30
            bubble_width = text_width + padding * 2
            bubble_height = text_height + padding * 2
            
            # Vị trí bong bóng (Góc dưới cùng ở giữa, chuẩn Webtoon)
            bubble_x = (width - bubble_width) // 2
            bubble_y = height - bubble_height - 50
            
            # Vẽ nền bong bóng (Màu trắng, bo tròn nhẹ)
            bubble_bbox = [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height]
            draw.rounded_rectangle(bubble_bbox, radius=20, fill=(255, 255, 255, 220), outline=(0, 0, 0, 255), width=3)
            
            # Vẽ tam giác chỉ xuống (đuôi bong bóng)
            tail_points = [
                (bubble_x + bubble_width // 2 - 15, bubble_y + bubble_height),
                (bubble_x + bubble_width // 2 + 15, bubble_y + bubble_height),
                (bubble_x + bubble_width // 2, bubble_y + bubble_height + 25)
            ]
            draw.polygon(tail_points, fill=(255, 255, 255, 220))
            draw.line([tail_points[0], tail_points[2]], fill=(0, 0, 0, 255), width=3)
            draw.line([tail_points[1], tail_points[2]], fill=(0, 0, 0, 255), width=3)
            
            # Chèn chữ vào bong bóng
            text_x = bubble_x + padding
            text_y = bubble_y + padding
            draw.multiline_text((text_x, text_y), wrapped_text, font=font, fill=(0, 0, 0, 255), align="center")
            
            # Convert lại sang RGB để lưu JPEG
            final_img = img.convert("RGB")
            final_img.save(output_path, "JPEG", quality=95)
            print(f"[SUCCESS] Mangstoon AI: Đã chèn bong bóng thoại Webtoon vào {output_path}")
            return True
            
    except Exception as e:
        print(f"[ERROR] Mangstoon AI Bubble Error: {e}")
        return False

def generate_webtoon_strip(image_paths: list, output_path: str) -> bool:
    """Nối dọc các ảnh thành một dải Webtoon dài (Vertical Scroll)."""
    if not image_paths:
        return False
        
    try:
        images = []
        for p in image_paths:
            if os.path.exists(p):
                try:
                    img = Image.open(p, encoding="utf-8")
                    images.append(img)
                except Exception:
                    pass
                    
        if not images:
            return False
            
        widths, heights = zip(*(i.size for i in images))
        
        max_width = max(widths)
        total_height = sum(heights) + (len(images) - 1) * 20 # Khoảng cách 20px giữa các khung
        
        new_im = Image.new('RGB', (max_width, total_height), color=(0, 0, 0))
        
        y_offset = 0
        for im in images:
            # Canh giữa nếu ảnh nhỏ hơn max_width
            x_offset = (max_width - im.width) // 2
            new_im.paste(im, (x_offset, y_offset))
            y_offset += im.height + 20
            
        new_im.save(output_path, "JPEG", quality=90)
        
        # Proper resource cleanup
        for img in images:
            img.close()
            
        print(f"[SUCCESS] Mangstoon AI: Đã tạo dải Webtoon cuộn dọc thành công tại {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Webtoon Strip Generation Error: {e}")
        return False

if __name__ == "__main__":
    # Test local
    print("Testing Mangstoon AI Layout module...")
