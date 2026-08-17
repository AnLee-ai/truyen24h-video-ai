import threading
import queue
import time
from typing import Callable, Dict, Any

class LightweightQueueManager:
    """
    A lightweight, thread-based job queue for Windows to avoid Redis dependency.
    Manages background tasks with limited concurrency.
    """
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.job_queue = queue.Queue()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.workers = []
        self._start_workers()

    def _cleanup_old_jobs(self):
        # Keep only the last 100 jobs to prevent memory leak
        if len(self.active_jobs) > 100:
            # Sort by queued_at and remove oldest completed/failed jobs
            old_jobs = sorted(self.active_jobs.items(), key=lambda x: x[1].get("queued_at", 0))
            for job_id, info in old_jobs:
                if info["status"] in ["completed", "failed"] and len(self.active_jobs) > 100:
                    del self.active_jobs[job_id]

    def _start_workers(self):
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"QueueWorker-{i}")
            t.start()
            self.workers.append(t)

    def _worker_loop(self):
        while True:
            job_id, func, args, kwargs = self.job_queue.get()
            try:
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
                    self.active_jobs[job_id]["error"] = str(e)
            finally:
                self.job_queue.task_done()

    def add_job(self, job_id: str, func: Callable, *args, **kwargs):
        """Adds a job to the queue."""
        self._cleanup_old_jobs()
        self.active_jobs[job_id] = {
            "status": "queued",
            "queued_at": time.time(),
            "start_time": None,
            "error": None
        }
        self.job_queue.put((job_id, func, args, kwargs))
        print(f"[QUEUE] 📥 Đã thêm Job {job_id} vào hàng đợi.")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Returns the status of a specific job."""
        return self.active_jobs.get(job_id, {"status": "not_found"})

    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Returns all tracked jobs."""
        return self.active_jobs

# Global instance for FastAPI to use
job_queue = LightweightQueueManager(max_workers=2)
