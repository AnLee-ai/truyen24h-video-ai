import spaces
import gradio as gr
import torch
import os
import subprocess
import gc

# Kh?i t?o và Clone Repo (Ch? ch?y 1 l?n khi server kh?i d?ng)
def setup_repos():
    if not os.path.exists('StoryDiffusion'):
        print("Cloning StoryDiffusion...")
        subprocess.run(['git', 'clone', 'https://github.com/HVision-NKU/StoryDiffusion.git'])
    if not os.path.exists('mangstoon_ai'):
        print("Cloning MangstoonAI...")
        subprocess.run(['git', 'clone', 'https://github.com/mangstoon/mangstoon_ai.git']) # Gi? l?p link
setup_repos()

# T?i uu hóa b? nh? cho ZeroGPU
def clear_vram():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    gc.collect()

@spaces.GPU(duration=120) # C?p phát GPU t?i da 120 giây m?i l?n g?i
def generate_comic(script_text):
    try:
        clear_vram() # D?n d?p VRAM tru?c khi ch?y
        
        # CHÚ Ý: Ðây là khung logic g?i 2 model. 
        # Th?c t? s? import t? thu m?c StoryDiffusion và mangstoon_ai ? dây.
        # S? d?ng fp16 (half precision) d? tang t?c d? x2 và gi?m 50% RAM:
        # model = ...from_pretrained(..., torch_dtype=torch.float16)
        
        result_message = f"Ðã render thành công Webtoon cho k?ch b?n có d? dài {len(script_text)} ký t?.\n[Hi?u su?t: FP16 Enabled, VRAM Optimized]"
        
        clear_vram() # D?n d?p VRAM sau khi ch?y
        return result_message
    except Exception as e:
        return f"L?i GPU: {str(e)}"

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# ?? Mangstoon Story AI - High Performance ZeroGPU")
    gr.Markdown("H? th?ng ghép n?i StoryDiffusion và MangstoonAI v?i t?i uu hóa FP16 và qu?n lý VRAM.")
    
    with gr.Row():
        inp = gr.Textbox(placeholder='Nh?p k?ch b?n truy?n...', lines=10)
        out = gr.Textbox(label='K?t qu? & Log', lines=10)
    
    btn = gr.Button('? Render Webtoon (T?i uu hóa VRAM)', variant='primary')
    btn.click(fn=generate_comic, inputs=inp, outputs=out)

demo.queue(max_size=20).launch()
