import sys
import re

content = open('src/video.py', 'r', encoding='utf-8').read()

# Remove dispatch_to_moneyprinter
match = re.search(r'def dispatch_to_moneyprinter.*?return ""\n', content, flags=re.DOTALL)
if match:
    content = content.replace(match.group(0), '')
    print('Removed dispatch_to_moneyprinter')
else:
    print('Warning: dispatch_to_moneyprinter not found')

# Remove moneyprinter call in render_novel_video
old_render = """    # Try moneyprinter first
    moneyprinter_vid = dispatch_to_moneyprinter(title, img_dir, audio_path)
    if moneyprinter_vid:
        return moneyprinter_vid
        
    return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7, chapter_id=chapter_id)"""

new_render = """    return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7, chapter_id=chapter_id)"""

if old_render in content:
    content = content.replace(old_render, new_render)
    print('Removed moneyprinter usage in render_novel_video')
else:
    print('Warning: old_render not found')

open('src/video.py', 'w', encoding='utf-8').write(content)
