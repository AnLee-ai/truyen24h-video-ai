import sys
import re

try:
    content = open('src/video.py', 'r', encoding='utf-8').read()
    
    # Replace function signature
    old_sig = 'def create_multi_image_slideshow_video(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel", interval: int = 7) -> str:'
    new_sig = 'def create_multi_image_slideshow_video(audio_path: str, srt_path: str, output_video_path: str, title: str = "Novel", interval: int = 7, chapter_id: str = "") -> str:'
    
    if old_sig in content:
        content = content.replace(old_sig, new_sig)
    else:
        print('Warning: Function signature not found exactly as expected.')
    
    # Replace function call in render_novel_video
    old_call = 'return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7)'
    new_call = 'return create_multi_image_slideshow_video(audio_path, srt_path, out_video, title, interval=7, chapter_id=chapter_id)'
    
    if old_call in content:
        content = content.replace(old_call, new_call)
    else:
        print('Warning: Function call not found exactly as expected.')

    open('src/video.py', 'w', encoding='utf-8').write(content)
    print('Patched src/video.py')
except Exception as e:
    print(f'Error: {e}')
