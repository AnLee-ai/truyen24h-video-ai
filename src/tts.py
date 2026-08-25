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
            if line.startswith("NOTE"):
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
            clean_text = re.sub(r'<[^>]+>', '', line)
            srt_lines.append(clean_text)
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

def split_text_into_chunks(text: str, max_chars: int = 1200) -> list:
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
            sentences = re.split(r'(?<!\.\.)(?<=[.?!])\s+', p)
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
        r"(\d{2}):(\d{2}):(\d{2}),(\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{1,3})"
    )
    
    def parse_time_to_ms(h, m, s, ms):
        ms_str = str(ms).ljust(3, '0')[:3]
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms_str)
        
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

def detect_speaker_role(text_segment: str, default_voice: str) -> tuple[str, str, str, str]:
    """Phân tích văn bản kịch bản để gán Đa Giọng Đọc Tiếng Việt Điện Ảnh (100% Thuần Việt)."""
    lower_segment = text_segment.lower()
    has_quotes = any(q in text_segment for q in ['"', '“', '”'])
    has_exclamation = '!' in text_segment or '！' in text_segment
    
    # 1. ☯️ Khẩu Quyết Thần Chú / Kinh Văn Tiên Hiệp (Giọng Tiếng Việt Nam Minh -5Hz)
    if any(kw in lower_segment for kw in ["khẩu quyết", "thần chú", "chu chú", "kinh văn", "ấn quyết", "thần thông bi"]):
        return ("vi-VN-NamMinhNeural", "-5Hz", "+0%", "☯️ Khẩu Quyết Thần Chú (Nam Minh -5Hz)")

    # 2. ⚡ Hống Thanh Chiến Đấu Kịch Tính (Giọng Tiếng Việt Nam Minh Nam Tính Hào Hùng)
    if has_exclamation and any(kw in lower_segment for kw in ["bộc phát", "tuyệt chiêu", "trùng sinh", "diệt cho ta", "chết đi"]):
        return ("vi-VN-NamMinhNeural", "+2Hz", "+15%", "⚡ Hống Thanh Chiến Đấu (Nam Minh +2Hz)")

    # 3. 🤖 Hệ Thống Thôn Phệ Vô Tận / Thông Báo AI (Giọng Công Nghệ Lạnh Băng, Vang Vọt)
    if any(kw in lower_segment for kw in ["hệ thống", "[thông báo]", "kích hoạt", "thôn phệ", "thăng cấp", "[nhiệm vụ]"]):
        return ("vi-VN-NamMinhNeural", "+0Hz", "+20%", "🤖 Hệ Thống Thôn Phệ (AI System)")
        
    # 4. 👿 Phản Diện / Tà Ma / Sát Thủ (Giọng U Tối, Ma Mị, Đáng Sợ)
    if any(kw in lower_segment for kw in ["tà ma", "phản diện", "sát thủ", "ma vương", "huyết tộc", "hắc y nhân", "kẻ địch"]):
        return ("vi-VN-NamMinhNeural", "-10Hz", "-5%", "👿 Phản Diện (Nam Minh -10Hz)")
        
    # 5. 🐉 Ma Thú / Quái Vật (Giọng Trầm Đục, Vang Rền)
    if any(kw in lower_segment for kw in ["ma thú", "yêu thú", "cổ long", "thần long", "gầm lên", "hung thú", "quái vật"]):
        return ("vi-VN-NamMinhNeural", "-12Hz", "-8%", "🐉 Quái Vật Thượng Cổ (Nam Minh -12Hz)")

    # 6. 👑 Nữ Đế / Nữ Vương / Boss Nữ (Giọng Quyến Rũ, Lạnh Lùng, Kiêu Hãnh)
    if any(kw in lower_segment for kw in ["nữ đế", "nữ vương", "công chúa", "boss nữ"]):
        return ("vi-VN-HoaiMyNeural", "-3Hz", "+6%", "👑 Nữ Đế / Nữ Vương (Hoài Mỹ -3Hz)")

    # 7. 🧙 Tiền Bối / Trưởng Lão (Giọng Trầm Ấm, Uy Nghiêm)
    if any(kw in lower_segment for kw in ["trưởng lão", "lão giả", "sư phụ", "tiền bối", "ông lão", "bà lão"]):
        return ("vi-VN-NamMinhNeural", "-6Hz", "-2%", "🧙 Tiền Bối (Nam Minh -6Hz)")
        
    # 8. 🧝 Nữ Phụ / Nữ Chính Thư Thái (Giọng Nữ Kiều Diễm, Thanh Cao)
    if any(kw in lower_segment for kw in ["tiểu thư", "tông chủ", "sư tỷ"]):
        return ("vi-VN-HoaiMyNeural", "+0Hz", "+8%", "🧝 Nữ Trưởng (Hoài Mỹ Standard)")
        
    # 9. 👶 Tiểu Đệ Tử / Đồng Tử / Trẻ Em (Giọng Ngây Thơ, Háo Hức)
    if has_quotes and any(kw in lower_segment for kw in ["đệ tử", "tiểu sư đệ", "tiểu tử", "đồng tử", "đứa bé"]):
        return ("vi-VN-HoaiMyNeural", "+4Hz", "+14%", "👶 Trẻ Em (Hoài Mỹ +4Hz)")

    # 10. 🌸 Thiếu Nữ (Giọng Nữ Ngọt Ngào, Trong Trẻo)
    if has_quotes and any(kw in lower_segment for kw in ["nàng", "cô gái", "thiếu nữ", "sư muội"]):
        return ("vi-VN-HoaiMyNeural", "+3Hz", "+10%", "🌸 Thiếu Nữ (Hoài Mỹ +3Hz)")
        
    # 11. 🔥 Nam Chính / Nam Nhân (Giọng Nam Ngạo Khí, Uy Phong)
    if has_quotes or any(kw in lower_segment for kw in ["hắn", "nam tử", "thiếu niên", "chàng", "cậu bé"]):
        rate_mod = "+15%" if has_exclamation else "+10%"
        return ("vi-VN-NamMinhNeural", "+2Hz", rate_mod, "🔥 Nam Chính (Nam Minh +2Hz)")
        
    # 12. 🎙️ Người Dẫn Chuyện Tiên Hiệp (Narrator Trầm Hùng, Lôi Cuốn)
    return ("vi-VN-NamMinhNeural", "+0Hz", "+8%", "🎙️ Người Dẫn Chuyện (Nam Minh Standard)")

def format_srt_youtube_style(srt_content: str, max_chars_per_line: int = 34) -> str:
    """Format subtitle text to YouTube CC style (wrap lines at max 34 chars to prevent screen overflow)."""
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    formatted_blocks = []
    
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) >= 3 and lines[0].isdigit() and '-->' in lines[1]:
            header = lines[:2]
            text = " ".join(lines[2:])
            
            # Wrap text into lines of max ~34 chars
            words = text.split()
            wrapped_lines = []
            curr_line = []
            curr_len = 0
            
            for w in words:
                if curr_len + len(w) + (1 if curr_line else 0) > max_chars_per_line:
                    if curr_line:
                        wrapped_lines.append(" ".join(curr_line))
                    curr_line = [w]
                    curr_len = len(w)
                else:
                    curr_line.append(w)
                    curr_len += len(w) + (1 if len(curr_line) > 1 else 0)
            if curr_line:
                wrapped_lines.append(" ".join(curr_line))
                
            formatted_blocks.append("\n".join(header + wrapped_lines))
        else:
            formatted_blocks.append(block)
            
    return "\n\n".join(formatted_blocks)

async def _run_tts_async(text: str, voice: str, rate: str, pitch: str, audio_path: str, srt_path: str):
    """Run edge-tts using fine-grained multi-lingual character voice acting and PARALLEL chunk synthesis."""
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

    # Chay song song voi semaphore gioi han 5 ket noi dong thoi tranh Connection Reset
    _tts_semaphore = asyncio.Semaphore(5)
    async def _throttled_chunk(idx, c_text):
        async with _tts_semaphore:
            return await _process_chunk(idx, c_text)
    tasks = [_throttled_chunk(idx, c_text) for idx, c_text in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    # Check for exceptions
    for res in chunk_results:
        if isinstance(res, Exception):
            print(f"[ERROR] TTS Chunk failed: {res}")
    # Filter out exceptions
    chunk_results = [r for r in chunk_results if not isinstance(r, Exception)]
    chunk_results.sort(key=lambda x: x[0])  # Giữ đúng thứ tự câu chuyện

    chunk_audio_paths = []
    total_srt_content = []
    offset_seconds = 0.0
    global_sub_idx = 1

    for idx, chunk_audio, chunk_srt in chunk_results:
        if not os.path.exists(chunk_srt):
            print(f"[WARNING] Chunk SRT not found, skipping subtitle for chunk {idx}: {chunk_srt}")
            chunk_audio_paths.append(chunk_audio)
            continue
        with open(chunk_srt, "r", encoding="utf-8") as f:
            srt_content = f.read()
            
        shifted_srt, last_timestamp_seconds = shift_srt_time(srt_content, offset_seconds, global_sub_idx)
        total_srt_content.append(shifted_srt)
        offset_seconds = last_timestamp_seconds
        
        block_matches = re.findall(r"^\d+$", srt_content, re.MULTILINE)
        global_sub_idx += len(block_matches)
        chunk_audio_paths.append(chunk_audio)

    # Concatenate all chunk mp3 files
    with open(audio_path, "wb") as final_audio:
        for p in chunk_audio_paths:
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                print(f"[WARNING] Chunk audio missing or empty, skipping: {p}")
                continue
            with open(p, "rb") as f:
                final_audio.write(f.read())
                
    # Save the merged shifted SRT file (YouTube style wrapped)
    raw_srt_text = "\n\n".join(total_srt_content)
    clean_srt_text = format_srt_youtube_style(raw_srt_text, max_chars_per_line=34)
    with open(srt_path, "w", encoding="utf-8") as final_srt:
        final_srt.write(clean_srt_text)
        
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
    pattern = r"(?im)^\s*[*_]*\s*(?:Dẫn lược|Giới thiệu|Phần dẫn lược|Tóm tắt bối cảnh|Prologue|Introduction|Giới thiệu bối cảnh)\s*[:：\-–—]*\s*[*_]*\s*[:：\-–—]*\s*"
    cleaned = re.sub(pattern, "", cleaned).strip()
    return cleaned

def generate_voice_and_subs(text: str, chapter_id: str) -> tuple:
    """
    Generate MP3 voice file and SRT subtitles for a chapter (with chunking).
    """
    text = clean_tts_text(text)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    audio_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}_raw.mp3")
    srt_path = os.path.join(config.OUTPUT_DIR, f"{chapter_id}.srt")
    
    print(f"[INFO] Synthesizing speech for chapter using voice {config.DEFAULT_VOICE}...")
    
    # Run the async loop; handle case where loop already exists (e.g. FastAPI background task)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _run_tts_async(
                    text=text, voice=config.DEFAULT_VOICE,
                    rate=config.DEFAULT_RATE, pitch=config.DEFAULT_PITCH,
                    audio_path=audio_path, srt_path=srt_path
                ))
                future.result()
        else:
            loop.run_until_complete(_run_tts_async(
                text=text, voice=config.DEFAULT_VOICE,
                rate=config.DEFAULT_RATE, pitch=config.DEFAULT_PITCH,
                audio_path=audio_path, srt_path=srt_path
            ))
    except RuntimeError:
        asyncio.run(_run_tts_async(
            text=text, voice=config.DEFAULT_VOICE,
            rate=config.DEFAULT_RATE, pitch=config.DEFAULT_PITCH,
            audio_path=audio_path, srt_path=srt_path
        ))
    
    # Check if final file is valid
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
         raise ValueError("No audio was received. Please verify that your parameters are correct.")
         
    return audio_path, srt_path