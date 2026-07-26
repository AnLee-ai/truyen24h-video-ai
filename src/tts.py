import asyncio
import os
import re
import edge_tts
from src import config

def vtt_to_srt(vtt_content: str) -> str:
    """Converts WebVTT subtitle format to SRT format."""
    lines = vtt_content.strip().split('\n')
    srt_lines = []
    block_idx = 1
    
    # Skip the WEBVTT header and optional empty lines
    skip_header = True
    
    for line in lines:
        if skip_header:
            if line.startswith("WEBVTT") or line.strip() == "":
                continue
            skip_header = False
            
        # Match time range line: e.g. 00:00:01.000 --> 00:00:03.000
        time_match = re.match(r"(\d{2}:\d{2}:\d{2})\.(\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2})\.(\d{3})", line)
        if time_match:
            # VTT uses dot (.) for milliseconds, SRT uses comma (,)
            start_hms, start_ms, end_hms, end_ms = time_match.groups()
            srt_lines.append(str(block_idx))
            srt_lines.append(f"{start_hms},{start_ms} --> {end_hms},{end_ms}")
            block_idx += 1
        elif line.strip() != "":
            srt_lines.append(line)
        else:
            srt_lines.append("") # empty line separator between blocks
            
    return "\n".join(srt_lines)

def sanitize_voice_name(voice: str) -> str:
    """Extract short voice name from Microsoft full voice name if needed."""
    match = re.search(r"\(([^,]+),\s*([^)]+)\)", voice)
    if match:
        lang, name = match.groups()
        return f"{lang.strip()}-{name.strip()}"
    return voice

def split_text_into_chunks(text: str, max_chars: int = 3000) -> list:
    """Split text into smaller chunks by paragraph or sentence to avoid edge-tts timeout/limits."""
    paragraphs = text.split("\n")
    chunks = []
    current_chunk: list[str] = []
    current_len = 0
    
    for p in paragraphs:
        if len(p) > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            # Split long paragraph by sentence
            sentences = re.split(r'(?<=[.?!])\s+', p)
            current_s_chunk: list[str] = []
            current_s_len = 0
            for s in sentences:
                if current_s_len + len(s) > max_chars:
                    if current_s_chunk:
                        chunks.append(" ".join(current_s_chunk))
                    current_s_chunk = [s]
                    current_s_len = len(s)
                else:
                    current_s_chunk.append(s)
                    current_s_len += len(s)
            if current_s_chunk:
                chunks.append(" ".join(current_s_chunk))
        else:
            if current_len + len(p) + 1 > max_chars:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [p]
                current_len = len(p)
            else:
                current_chunk.append(p)
                current_len += len(p) + 1
                
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

def shift_srt_time(srt_content: str, offset_seconds: float, start_index: int) -> tuple[str, float]:
    """Shift timestamps and reindex SRT subtitle blocks."""
    if not srt_content.strip():
        return "", offset_seconds
        
    lines = srt_content.splitlines()
    shifted_lines = []
    
    timestamp_pattern = re.compile(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    )
    
    def parse_time_to_ms(h, m, s, ms):
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)
        
    def format_ms_to_time(total_ms):
        total_s, ms = divmod(total_ms, 1000)
        total_m, s = divmod(total_s, 60)
        h, m = divmod(total_m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
    offset_ms = int(offset_seconds * 1000)
    max_ms = offset_ms
    
    current_idx = start_index
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            shifted_lines.append("")
            idx += 1
            continue
            
        if re.match(r"^\d+$", line):
            shifted_lines.append(str(current_idx))
            current_idx += 1
            idx += 1
            continue
            
        match = timestamp_pattern.match(line)
        if match:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
            ms_start = parse_time_to_ms(h1, m1, s1, ms1) + offset_ms
            ms_end = parse_time_to_ms(h2, m2, s2, ms2) + offset_ms
            max_ms = max(max_ms, ms_end)
            shifted_lines.append(f"{format_ms_to_time(ms_start)} --> {format_ms_to_time(ms_end)}")
        else:
            shifted_lines.append(lines[idx])
        idx += 1
        
    return "\n".join(shifted_lines), max_ms / 1000.0

async def _run_tts_chunk_async(text: str, voice: str, rate: str, pitch: str, audio_path: str, srt_path: str, max_retries: int = 5):
    """Run edge-tts for a single text chunk with retry logic and timeout."""
    voice = sanitize_voice_name(voice)
    
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            submaker = edge_tts.SubMaker()
            
            async def write_stream():
                with open(audio_path, "wb") as audio_file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])
                        elif chunk["type"] in ("WordBoundary", "SentenceBoundary", "Metadata"):
                            submaker.feed(chunk)
            
            # 90 second timeout for a single chunk synthesis to prevent hanging on slow network
            await asyncio.wait_for(write_stream(), timeout=90.0)
                        
            # Verify that the audio file is valid
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                with open(srt_path, "w", encoding="utf-8") as srt_file:
                    srt_file.write(submaker.get_srt())
                return  # Success!
                
            print(f"[WARNING] TTS attempt {attempt+1} generated empty file. Retrying...")
        except Exception as e:
            err_msg = str(e) or "TimeoutError"
            print(f"[WARNING] TTS attempt {attempt+1} failed with error: {err_msg}. Retrying...")
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2)  # Wait 2 seconds before retrying
            
    raise ValueError("No audio was received. Please verify that your parameters are correct.")

async def _run_tts_async(text: str, voice: str, rate: str, pitch: str, audio_path: str, srt_path: str):
    """Run edge-tts using text chunking and SRT merging."""
    chunks = split_text_into_chunks(text)
    print(f"[INFO] Text split into {len(chunks)} chunks for speech synthesis.")
    
    chunk_audio_paths = []
    total_srt_content = []
    offset_seconds = 0.0
    global_sub_idx = 1
    
    for idx, chunk_text in enumerate(chunks):
        chunk_audio = f"{audio_path}_chunk_{idx}.mp3"
        chunk_srt = f"{srt_path}_chunk_{idx}.srt"
        
        await _run_tts_chunk_async(chunk_text, voice, rate, pitch, chunk_audio, chunk_srt)
        
        # Check if the chunk audio was actually written and is not empty
        if not os.path.exists(chunk_audio) or os.path.getsize(chunk_audio) == 0:
            raise ValueError(f"Failed to generate audio for chunk {idx}. Server returned empty data.")
            
        with open(chunk_srt, "r", encoding="utf-8") as f:
            srt_content = f.read()
            
        shifted_srt, last_timestamp_seconds = shift_srt_time(srt_content, offset_seconds, global_sub_idx)
        total_srt_content.append(shifted_srt)
        offset_seconds = last_timestamp_seconds
        
        # Count how many subtitle blocks were in this chunk
        block_matches = re.findall(r"^\d+$", srt_content, re.MULTILINE)
        global_sub_idx += len(block_matches)
        
        chunk_audio_paths.append(chunk_audio)
        
    # Concatenate all chunk mp3 files
    with open(audio_path, "wb") as final_audio:
        for p in chunk_audio_paths:
            with open(p, "rb") as f:
                final_audio.write(f.read())
                
    # Save the merged shifted SRT file
    with open(srt_path, "w", encoding="utf-8") as final_srt:
        final_srt.write("\n\n".join(total_srt_content))
        
    # Clean up temporary chunk files
    for p in chunk_audio_paths:
        try:
            os.remove(p)
        except Exception:
            pass
    for idx in range(len(chunks)):
        try:
            os.remove(f"{srt_path}_chunk_{idx}.srt")
        except Exception:
            pass

def clean_tts_text(text: str) -> str:
    """Sanitize chapter text before TTS to remove unwanted section titles like 'Dẫn lược', 'Chương X', etc."""
    cleaned = text.strip()
    pattern = r"^\s*(?:\*\*|\*|__|_)*\s*(?:Dẫn lược|Giới thiệu|Phần dẫn lược|Tóm tắt bối cảnh|Prologue|Introduction|Chương\s*\d+|Giới thiệu bối cảnh)\s*(?:\*\*|\*|__|_)*\s*[:：\-–—\n]?\s*(?:\*\*|\*|__|_)*\s*"
    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned

def generate_voice_and_subs(text: str, chapter_id: str) -> tuple:
    """
    Generate MP3 voice file and SRT subtitles for a chapter (with chunking).
    """
    text = clean_tts_text(text)
    audio_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}_raw.mp3")
    srt_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}.srt")
    
    print(f"[INFO] Synthesizing speech for chapter using voice {config.DEFAULT_VOICE}...")
    
    # Run the async loop inside the sync wrapper to generate audio and srt directly
    asyncio.run(_run_tts_async(
        text=text,
        voice=config.DEFAULT_VOICE,
        rate=config.DEFAULT_RATE,
        pitch=config.DEFAULT_PITCH,
        audio_path=audio_path,
        srt_path=srt_path
    ))
    
    # Check if final file is valid
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
         raise ValueError("No audio was received. Please verify that your parameters are correct.")
         
    return audio_path, srt_path