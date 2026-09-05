import sys

try:
    content = open('src/video.py', 'r', encoding='utf-8').read()
    
    # 1. Simplify Video Filter (Remove slow unsharp and eq)
    old_vf = '"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,unsharp=5:5:1.0:5:5:0.0,eq=brightness=0.04:contrast=1.12:saturation=1.22[bg]"'
    new_vf = '"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080[bg]"'
    content = content.replace(old_vf, new_vf)
    
    # Do it for Pass 3 as well
    old_vf_pass3 = '"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,unsharp=5:5:1.0:5:5:0.0"'
    new_vf_pass3 = '"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"'
    content = content.replace(old_vf_pass3, new_vf_pass3)

    # 2. Change CPU Preset to ultrafast
    old_opts = 'encoder_opts = ["-preset", "medium", "-threads", "0", "-crf", "18"]'
    new_opts = 'encoder_opts = ["-preset", "ultrafast", "-tune", "stillimage", "-threads", "0", "-crf", "24"]'
    content = content.replace(old_opts, new_opts)
    
    # 3. Change Framerate from 25 to 15 in Pass 1
    old_fps_pass1 = '"-vsync", "1", "-async", "1", "-r", "25",'
    new_fps_pass1 = '"-vsync", "1", "-async", "1", "-r", "15",'
    content = content.replace(old_fps_pass1, new_fps_pass1)

    # 4. Change Framerate from 20 to 15 in Pass 2 and Pass 3
    old_fps_pass2 = '"-r", "20",'
    new_fps_pass2 = '"-r", "15",'
    content = content.replace(old_fps_pass2, new_fps_pass2)

    # 5. Remove contradictory bitrate flags that slow down ultrafast
    old_bitrate = '"-b:v", "8000k", "-maxrate", "12000k", "-bufsize", "16000k",'
    new_bitrate = ' '
    content = content.replace(old_bitrate, new_bitrate)

    open('src/video.py', 'w', encoding='utf-8').write(content)
    print('Patched src/video.py for massive speedup')
except Exception as e:
    print(f'Error: {e}')
