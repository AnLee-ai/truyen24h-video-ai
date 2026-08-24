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
        
    if not os.path.exists('inkos'):
        print("Cloning Inkos...")
        subprocess.run(['git', 'clone', 'https://github.com/Narcooo/inkos.git'])
        print("Installing pnpm and building Inkos...")
        subprocess.run('npm install -g pnpm', shell=True)
        subprocess.run('cd inkos && pnpm install && pnpm run build', shell=True)
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

# Inkos Text Generator Function
def generate_story(prompt):
    try:
        # Run inkos via Node.js
        cmd = f'node inkos/packages/cli/dist/index.js interact --message "{prompt}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=os.environ.copy())
        if result.returncode != 0:
            return f"Lỗi Inkos: {result.stderr}"
        return result.stdout.strip()
    except Exception as e:
        return f"Lỗi hệ thống Inkos: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("# 🎨 Mangstoon & Inkos AI - ZeroGPU API")
    
    with gr.Tab("Tạo Ảnh (StoryDiffusion)"):
        img_inp = gr.Textbox(placeholder='Nhập kịch bản vẽ ảnh...', lines=5)
        img_btn = gr.Button('🚀 Vẽ Ảnh', variant='primary')
        with gr.Row():
            img_out_gallery = gr.Gallery(label='Kết quả Ảnh')
            img_out_log = gr.Textbox(label='Log')
        img_btn.click(fn=generate_comic, inputs=img_inp, outputs=[img_out_gallery, img_out_log], api_name="predict")

    with gr.Tab("Tạo Kịch Bản (Inkos)"):
        txt_inp = gr.Textbox(placeholder='Nhập yêu cầu viết truyện...', lines=5)
        txt_btn = gr.Button('✍️ Viết Kịch Bản', variant='primary')
        txt_out = gr.Textbox(label='Kết quả Inkos', lines=10)
        txt_btn.click(fn=generate_story, inputs=txt_inp, outputs=txt_out, api_name="generate_story")

demo.queue(max_size=20).launch()
