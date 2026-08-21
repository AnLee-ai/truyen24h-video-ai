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

# 1. src/task_manager.py (C6, C7)
old_tm_worker = '''    async def _worker(self):
        import queue
        while not self.queue.empty():
            task_id, sync_func, args = await self.queue.get()'''
new_tm_worker = '''    async def _worker(self):
        import queue as _queue
        while True:
            try:
                import asyncio
                task_id, sync_func, args = await asyncio.wait_for(self.queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                if self.queue.empty(): break
                continue'''
replace_in_file('src/task_manager.py', old_tm_worker, new_tm_worker)

old_tm_kwargs = '''                # Provide log_callback to the kwargs of the sync_func
                kwargs = {"log_callback": log_callback, "is_cancelled": is_cancelled}
                
                # Start the sync function in a thread
                loop = asyncio.get_running_loop()
                future = loop.run_in_executor(None, lambda: sync_func(*args, **kwargs))'''
new_tm_kwargs = '''                # Provide log_callback to the kwargs of the sync_func
                import inspect
                sig = inspect.signature(sync_func)
                kwargs = {"log_callback": log_callback}
                if "is_cancelled" in sig.parameters: kwargs["is_cancelled"] = is_cancelled
                
                # Start the sync function in a thread
                loop = asyncio.get_running_loop()
                future = loop.run_in_executor(None, lambda: sync_func(*args, **kwargs))'''
replace_in_file('src/task_manager.py', old_tm_kwargs, new_tm_kwargs)

# 2. src/task_manager.py (H10)
old_tm_bcast = '''    async def broadcast(self, message: dict):
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WS: {e}")'''
new_tm_bcast = '''    async def broadcast(self, message: dict):
        dead = []
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WS: {e}")
                dead.append(ws)
        for ws in dead: self.websockets.remove(ws)'''
replace_in_file('src/task_manager.py', old_tm_bcast, new_tm_bcast)

# 3. src/queue_manager.py (H9)
old_qm_init = '''    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.job_queue = queue.Queue()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.workers = []'''
new_qm_init = '''    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.job_queue = queue.Queue()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        import threading
        self._lock = threading.Lock()
        self.workers = []'''
replace_in_file('src/queue_manager.py', old_qm_init, new_qm_init)

old_qm_worker = '''            try:
                if job_id in self.active_jobs:
                    self.active_jobs[job_id]["status"] = "processing"
                    self.active_jobs[job_id]["start_time"] = time.time()
                
                print(f"[QUEUE] 🚀 Bắt đầu xử lý Job {job_id}")
                func(*args, **kwargs)
                
                if job_id in self.active_jobs:
                    self.active_jobs[job_id]["status"] = "completed"
                print(f"[QUEUE] ✅ Đã hoàn thành Job {job_id}")
            except Exception as e:
                print(f"[QUEUE] ❌ Lỗi xử lý Job {job_id}: {e}")
                if job_id in self.active_jobs:
                    self.active_jobs[job_id]["status"] = "failed"
                    self.active_jobs[job_id]["error"] = str(e)'''
new_qm_worker = '''            try:
                with self._lock:
                    if job_id in self.active_jobs:
                        self.active_jobs[job_id]["status"] = "processing"
                        self.active_jobs[job_id]["start_time"] = time.time()
                
                print(f"[QUEUE] 🚀 Bắt đầu xử lý Job {job_id}")
                func(*args, **kwargs)
                
                with self._lock:
                    if job_id in self.active_jobs:
                        self.active_jobs[job_id]["status"] = "completed"
                print(f"[QUEUE] ✅ Đã hoàn thành Job {job_id}")
            except Exception as e:
                print(f"[QUEUE] ❌ Lỗi xử lý Job {job_id}: {e}")
                with self._lock:
                    if job_id in self.active_jobs:
                        self.active_jobs[job_id]["status"] = "failed"
                        self.active_jobs[job_id]["error"] = str(e)'''
replace_in_file('src/queue_manager.py', old_qm_worker, new_qm_worker)

old_qm_add = '''        self._cleanup_old_jobs()
        self.active_jobs[job_id] = {
            "status": "queued",
            "queued_at": time.time(),
            "start_time": None,
            "error": None
        }'''
new_qm_add = '''        with self._lock:
            self._cleanup_old_jobs()
            self.active_jobs[job_id] = {
                "status": "queued",
                "queued_at": time.time(),
                "start_time": None,
                "error": None
            }'''
replace_in_file('src/queue_manager.py', old_qm_add, new_qm_add)

# 4. src/database.py (H6, H7, H8)
old_db_update1 = '''            if chapter_number > 0:
                client.table("chapters").update(db_data).eq("chapter_number", chapter_number).execute()'''
new_db_update1 = '''            if chapter_number > 0 and novel_id:
                client.table("chapters").update(db_data).eq("novel_id", novel_id).eq("chapter_number", chapter_number).execute()'''
replace_in_file('src/database.py', old_db_update1, new_db_update1)

old_db_update2 = '''            if chapter_number > 0:
                client.table("chapters").update(safe_db_data).eq("chapter_number", chapter_number).execute()'''
new_db_update2 = '''            if chapter_number > 0 and novel_id:
                client.table("chapters").update(safe_db_data).eq("novel_id", novel_id).eq("chapter_number", chapter_number).execute()'''
replace_in_file('src/database.py', old_db_update2, new_db_update2)

old_db_lore = '''existing = client.table("world_lore").select("id").eq("keyword", keyword).execute()'''
new_db_lore = '''existing = client.table("world_lore").select("id").eq("novel_id", novel_id).eq("keyword", keyword).execute()'''
replace_in_file('src/database.py', old_db_lore, new_db_lore)

old_db_thread = '''existing = client.table("narrative_threads").select("id").eq("thread_name", thread_name).execute()'''
new_db_thread = '''existing = client.table("narrative_threads").select("id").eq("novel_id", novel_id).eq("thread_name", thread_name).execute()'''
replace_in_file('src/database.py', old_db_thread, new_db_thread)

# 5. templates/app.js (H3, H4)
old_js_parse = '''        currentEventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.msg) {'''
new_js_parse = '''        currentEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.msg) {'''
replace_in_file('templates/app.js', old_js_parse, new_js_parse)

old_js_parse_end = '''            if (data.done) {
                currentEventSource.close();
                currentEventSource = null;
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }
        };'''
new_js_parse_end = '''            if (data.done) {
                currentEventSource.close();
                currentEventSource = null;
                setButtonsState(false);
                appendLog('[INFO] Đã ngắt kết nối.', 'info');
            }
            } catch (e) {
                appendLog('[ERROR] Parse error: ' + e, 'error');
            }
        };'''
replace_in_file('templates/app.js', old_js_parse_end, new_js_parse_end)

old_js_err1 = '''tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${data.message}</td></tr>`;'''
new_js_err1 = '''tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="color:red">Lỗi: ${escapeHTML(data.message || 'Lỗi không xác định')}</td></tr>`;'''
replace_in_file('templates/app.js', old_js_err1, new_js_err1)

print('Patch3 complete!')
