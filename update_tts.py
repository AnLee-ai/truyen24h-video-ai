import re

with open(r'd:\222\src\tts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the info print and chunk processing logic
new_logic = '''
    chunks = split_text_into_chunks(text)
    print(f"[INFO] Bắt đầu tạo audio ({len(chunks)} Chunks) với giọng {voice}...")
    
    async def _process_chunk(idx: int, chunk_text: str):
        chunk_audio = f"{audio_path}_chunk_{idx}.mp3"
        chunk_srt = f"{srt_path}_chunk_{idx}.srt"
        print(f"   -> [Chunk {idx+1}/{len(chunks)}] Voice: {voice} (Pitch: {pitch}, Rate: {rate})")
        await _run_tts_chunk_async(chunk_text, voice, rate, pitch, chunk_audio, chunk_srt)
        if not os.path.exists(chunk_audio) or os.path.getsize(chunk_audio) == 0:
            raise ValueError(f"Failed to generate audio for chunk {idx}. Empty data.")
        return idx, chunk_audio, chunk_srt
'''

content = re.sub(r'chunks = split_text_into_chunks\(text\)\n.*?return idx, chunk_audio, chunk_srt', new_logic.strip(), content, flags=re.DOTALL)

with open(r'd:\222\src\tts.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated tts.py!")
