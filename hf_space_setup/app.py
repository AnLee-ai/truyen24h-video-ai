import spaces
import gradio as gr
import torch
import os
import subprocess
import gc
from PIL import Image

# Clone necessary repos
def setup_repos():
    if not os.path.exists('StoryDiffusion'):
        print("Cloning StoryDiffusion...")
        subprocess.run(['git', 'clone', 'https://github.com/HVision-NKU/StoryDiffusion.git'])
    # mangstoon_ai is a local repo, it might fail to clone if the URL is wrong. 
    # Try to clone, but if it fails, it means the user needs to upload the folder manually to HF.
    if not os.path.exists('mangstoon_ai'):
        print("Cloning MangstoonAI...")
        res = subprocess.run(['git', 'clone', 'https://github.com/mangstoon/mangstoon_ai.git'])
        if res.returncode != 0:
            print("WARNING: Could not clone mangstoon_ai. Please upload the mangstoon_ai folder manually to Hugging Face!")
            
setup_repos()

try:
    from diffusers import StableDiffusionXLPipeline
    has_diffusers = True
except ImportError:
    has_diffusers = False

pipe = None

def clear_vram():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    gc.collect()

@spaces.GPU(duration=120)
def generate_comic(script_text):
    global pipe
    try:
        clear_vram()
        
        if pipe is None:
            if has_diffusers:
                pipe = StableDiffusionXLPipeline.from_pretrained(
                    "stabilityai/stable-diffusion-xl-base-1.0", 
                    torch_dtype=torch.float16, 
                    variant="fp16"
                )
                pipe = pipe.to("cuda")
            else:
                return None, "Error: diffusers not installed."

        prompts = [p.strip() for p in script_text.split('\n') if p.strip()]
        if not prompts:
            prompts = ["A highly detailed anime illustration of a character"]

        images = []
        for prompt in prompts[:3]:
            image = pipe(prompt, num_inference_steps=20).images[0]
            images.append(image)

        clear_vram()
        return images, f"Đã tạo {len(images)} ảnh thành công."
    except Exception as e:
        return None, f"Lỗi GPU: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("# 🎨 Mangstoon Story AI - High Performance ZeroGPU (API Ready)")
    gr.Markdown("Hệ thống sinh ảnh AI truyện tranh. Tự động tải repository khi khởi động.")
    
    with gr.Row():
        inp = gr.Textbox(placeholder='Nhập kịch bản truyện... Mỗi dòng 1 cảnh.', lines=5)
    
    btn = gr.Button('🚀 Render Webtoon (Tối ưu hóa VRAM)', variant='primary')
    
    with gr.Row():
        out_gallery = gr.Gallery(label='Kết quả Ảnh')
        out_log = gr.Textbox(label='Log')
    
    btn.click(fn=generate_comic, inputs=inp, outputs=[out_gallery, out_log])

demo.queue(max_size=20).launch()

