import asyncio
import uuid
from loguru import logger
from fastapi import WebSocket

class TaskManager:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.active_tasks = {}
        self.websockets = []
        self._worker_task = None
        self.cancelled_tasks = set()

    async def connect_ws(self, websocket: WebSocket):
        await websocket.accept()
        self.websockets.append(websocket)
        logger.info(f"WebSocket connected. Total clients: {len(self.websockets)}")
        
    def disconnect_ws(self, websocket: WebSocket):
        if websocket in self.websockets:
            self.websockets.remove(websocket)
            logger.info(f"WebSocket disconnected. Total clients: {len(self.websockets)}")

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WS: {e}")
                dead.append(ws)
        for ws in dead:
            self.websockets.remove(ws)

    def is_task_running(self, task_id: str) -> bool:
        return task_id in self.active_tasks
        
    async def cancel_task(self, task_id: str):
        if self.is_task_running(task_id):
            self.cancelled_tasks.add(task_id)
            await self.broadcast({"type": "status", "task_id": task_id, "status": "cancelling"})
            logger.info(f"Requested cancellation for task {task_id}")
            return True
        return False

    async def add_task(self, task_id: str, sync_func, *args, task_type="pipeline"):
        if self.is_task_running(task_id):
            return False
            
        if task_id in self.cancelled_tasks:
            self.cancelled_tasks.remove(task_id)
            
        self.active_tasks[task_id] = {"status": "queued", "type": task_type}
        await self.queue.put((task_id, sync_func, args))
        await self.broadcast({"type": "status", "task_id": task_id, "status": "queued"})
        logger.info(f"Task {task_id} added to queue.")
        
        # Start worker if not running
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())
        return True

    async def _worker(self):
        import queue as _queue
        while True:
            try:
                task_id, sync_func, args = await asyncio.wait_for(self.queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # No new tasks in 30s — check if still needed
                if self.queue.empty():
                    break
                continue
            
            if task_id in self.cancelled_tasks:
                self.cancelled_tasks.remove(task_id)
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                await self.broadcast({"type": "status", "task_id": task_id, "status": "cancelled"})
                self.queue.task_done()
                continue
                
            self.active_tasks[task_id]["status"] = "running"
            await self.broadcast({"type": "status", "task_id": task_id, "status": "running"})
            logger.info(f"Worker started task {task_id}")
            
            log_queue = _queue.Queue()
            def log_callback(msg):
                log_queue.put(msg)
                
            def is_cancelled():
                return task_id in self.cancelled_tasks
                
            try:
                # Only pass log_callback; is_cancelled is optional (accepted via **kwargs)
                import inspect
                sig = inspect.signature(sync_func)
                extra_kwargs = {"log_callback": log_callback}
                if "is_cancelled" in sig.parameters:
                    extra_kwargs["is_cancelled"] = is_cancelled
                
                # Start the sync function in a thread
                loop = asyncio.get_running_loop()
                future = loop.run_in_executor(None, lambda: sync_func(*args, **extra_kwargs))
                
                while not future.done() or not log_queue.empty():
                    try:
                        while not log_queue.empty():
                            msg = log_queue.get_nowait()
                            # Broadcast the log message immediately
                            asyncio.create_task(self.broadcast({
                                "type": "log",
                                "task_id": task_id,
                                "msg": msg
                            }))
                    except Exception:
                        pass
                    await asyncio.sleep(0.1)
                
                # Wait for the thread to completely finish
                await future
                
                if task_id in self.cancelled_tasks:
                    self.active_tasks[task_id]["status"] = "cancelled"
                    await self.broadcast({"type": "status", "task_id": task_id, "status": "cancelled"})
                    self.cancelled_tasks.remove(task_id)
                else:
                    self.active_tasks[task_id]["status"] = "completed"
                    await self.broadcast({"type": "status", "task_id": task_id, "status": "completed"})
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self.active_tasks[task_id]["status"] = "failed"
                await self.broadcast({"type": "status", "task_id": task_id, "status": "failed", "error": str(e)})
            finally:
                self.queue.task_done()
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                logger.info(f"Worker finished task {task_id}")

task_manager = TaskManager()
