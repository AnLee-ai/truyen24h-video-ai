import os

def replace_in_file(path, old, new):
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Patched {path}')
    else:
        print(f'Failed to patch {path}')

# 6. src/tts.py (H11, H12)
old_tts_gather = '''    chunk_results = await asyncio.gather(*tasks)'''
new_tts_gather = '''    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    # Check for exceptions
    for res in chunk_results:
        if isinstance(res, Exception):
            print(f"[ERROR] TTS Chunk failed: {res}")
    # Filter out exceptions
    chunk_results = [r for r in chunk_results if not isinstance(r, Exception)]'''
replace_in_file('src/tts.py', old_tts_gather, new_tts_gather)

old_tts_loop = '''    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run async function in synchronous wrapper
    return loop.run_until_complete(_async_generate(text, chapter_id))'''
new_tts_loop = '''    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an event loop (e.g. from FastAPI), run as a task or block synchronously
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run_coroutine_threadsafe(_async_generate(text, chapter_id), loop).result()
    else:
        return asyncio.run(_async_generate(text, chapter_id))'''
replace_in_file('src/tts.py', old_tts_loop, new_tts_loop)

# 7. src/api/routers/pipelines.py (H13)
old_pl_thumbnail = '''@router.get("/run_thumbnail")
async def api_run_thumbnail(novel_id: str):
    async def event_generator():'''
new_pl_thumbnail = '''from fastapi import Request
@router.get("/run_thumbnail")
async def api_run_thumbnail(novel_id: str, request: Request = None):
    async def event_generator():'''
replace_in_file('src/api/routers/pipelines.py', old_pl_thumbnail, new_pl_thumbnail)

old_pl_loop = '''        while True:
            status = job_queue.get_job_status(job_id)
            if status["status"] == "completed":
                yield f"data: {json.dumps({'msg': '[SUCCESS] Hoàn thành! Kiểm tra logs trên terminal.', 'done': True})}\n\n"
                break
            elif status["status"] == "failed":
                err = status.get('error', 'Unknown')
                yield f"data: {json.dumps({'msg': f'[ERROR] Lỗi: {err}', 'done': True})}\n\n"
                break
            await asyncio.sleep(1.0)'''
new_pl_loop = '''        start_time = time.time()
        while True:
            if request and await request.is_disconnected():
                print("[WARNING] Client ngắt kết nối khi đang tạo thumbnail.")
                break
            if time.time() - start_time > 300:
                yield f"data: {json.dumps({'msg': '[ERROR] Timeout sau 5 phút.', 'done': True})}\n\n"
                break
            status = job_queue.get_job_status(job_id)
            if status["status"] == "completed":
                yield f"data: {json.dumps({'msg': '[SUCCESS] Hoàn thành! Kiểm tra logs trên terminal.', 'done': True})}\n\n"
                break
            elif status["status"] == "failed":
                err = status.get('error', 'Unknown')
                yield f"data: {json.dumps({'msg': f'[ERROR] Lỗi: {err}', 'done': True})}\n\n"
                break
            await asyncio.sleep(1.0)'''
replace_in_file('src/api/routers/pipelines.py', old_pl_loop, new_pl_loop)

# 8. src/writer.py (H14)
old_wr_parse = '''                    resp_json = response.json()
                    content = resp_json["choices"][0]["message"]["content"]
                    if content and len(content.strip().split()) > 10:'''
new_wr_parse = '''                    resp_json = response.json()
                    try:
                        content = resp_json["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError):
                        continue
                    if content and len(content.strip().split()) > 10:'''
replace_in_file('src/writer.py', old_wr_parse, new_wr_parse)

print('Patch4 complete!')
