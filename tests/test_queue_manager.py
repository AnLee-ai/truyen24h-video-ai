# -*- coding: utf-8 -*-
"""Test module: queue_manager.py - Kiểm tra job queue thread-safe."""
import time
import threading
import pytest

from src.queue_manager import LightweightQueueManager


@pytest.fixture
def qm():
    """Tạo queue manager riêng cho mỗi test."""
    return LightweightQueueManager(max_workers=2)


class TestAddAndGetJob:
    def test_add_job_status_queued(self, qm):
        qm.add_job("job-1", lambda: time.sleep(10))
        status = qm.get_job_status("job-1")
        assert status["status"] in ("queued", "processing")

    def test_job_completes_successfully(self, qm):
        result_holder = []
        qm.add_job("job-ok", lambda: result_holder.append("done"))
        time.sleep(0.5)
        assert qm.get_job_status("job-ok")["status"] == "completed"
        assert result_holder == ["done"]

    def test_job_failure_status(self, qm):
        def fail():
            raise ValueError("boom")
        qm.add_job("job-fail", fail)
        time.sleep(0.5)
        status = qm.get_job_status("job-fail")
        assert status["status"] == "failed"
        assert "boom" in status["error"]

    def test_not_found_job(self, qm):
        status = qm.get_job_status("nonexistent")
        assert status["status"] == "not_found"


class TestGetAllJobs:
    def test_returns_all_tracked(self, qm):
        qm.add_job("a", lambda: None)
        qm.add_job("b", lambda: None)
        time.sleep(0.5)
        all_jobs = qm.get_all_jobs()
        assert "a" in all_jobs
        assert "b" in all_jobs


class TestCleanupOldJobs:
    def test_cleanup_keeps_under_limit(self, qm):
        # Thêm 105 job hoàn thành
        for i in range(105):
            qm.add_job(f"old-{i}", lambda: None)
        time.sleep(2)
        # Thêm 1 job mới trigger cleanup
        qm.add_job("trigger", lambda: None)
        time.sleep(0.5)
        assert len(qm.get_all_jobs()) <= 101


class TestConcurrency:
    def test_multiple_jobs_concurrent(self, qm):
        results = []
        lock = threading.Lock()

        def worker(val):
            time.sleep(0.1)
            with lock:
                results.append(val)

        for i in range(5):
            qm.add_job(f"concurrent-{i}", worker, i)
        time.sleep(2)
        assert sorted(results) == [0, 1, 2, 3, 4]
