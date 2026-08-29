# -*- coding: utf-8 -*-
"""Test module: checkpoint.py - Kiểm tra load/save/mark checkpoint."""
import os
import json
import tempfile
import pytest
from unittest.mock import patch

from src.checkpoint import (
    get_checkpoint_path,
    load_checkpoint,
    save_checkpoint,
    mark_step_done,
    is_step_done,
)


@pytest.fixture
def tmp_output(tmp_path, monkeypatch):
    """Tạo thư mục output tạm để test không ảnh hưởng disk thật."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestGetCheckpointPath:
    def test_returns_correct_path(self, tmp_output):
        path = get_checkpoint_path("ch01")
        assert path.endswith(os.path.join("output", "ch01", "checkpoint.json"))

    def test_creates_directory(self, tmp_output):
        path = get_checkpoint_path("ch_new")
        assert os.path.isdir(os.path.dirname(path))


class TestLoadCheckpoint:
    def test_default_when_no_file(self, tmp_output):
        data = load_checkpoint("nonexistent")
        assert data["is_written"] is False
        assert data["is_audio_done"] is False
        assert data["video_path"] == ""

    def test_loads_existing_file(self, tmp_output):
        # Tạo file checkpoint trước
        save_checkpoint("ch_load", {"is_written": True, "custom_key": "abc"})
        data = load_checkpoint("ch_load")
        assert data["is_written"] is True
        assert data["custom_key"] == "abc"

    def test_returns_default_on_corrupt_json(self, tmp_output):
        path = get_checkpoint_path("ch_corrupt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{corrupt json!!!")
        data = load_checkpoint("ch_corrupt")
        assert data["is_written"] is False  # fallback mặc định


class TestSaveCheckpoint:
    def test_save_and_reload(self, tmp_output):
        save_checkpoint("ch_save", {"is_written": True, "audio_path": "/tmp/a.mp3"})
        data = load_checkpoint("ch_save")
        assert data["is_written"] is True
        assert data["audio_path"] == "/tmp/a.mp3"

    def test_save_unicode(self, tmp_output):
        save_checkpoint("ch_vn", {"title": "Chương 1: Thức Tỉnh"})
        data = load_checkpoint("ch_vn")
        assert data["title"] == "Chương 1: Thức Tỉnh"


class TestMarkStepDone:
    def test_marks_step_and_kwargs(self, tmp_output):
        mark_step_done("ch_mark", "is_audio_done", audio_path="/tmp/voice.mp3")
        data = load_checkpoint("ch_mark")
        assert data["is_audio_done"] is True
        assert data["audio_path"] == "/tmp/voice.mp3"

    def test_preserves_previous_data(self, tmp_output):
        mark_step_done("ch_multi", "is_written")
        mark_step_done("ch_multi", "is_audio_done")
        data = load_checkpoint("ch_multi")
        assert data["is_written"] is True
        assert data["is_audio_done"] is True


class TestIsStepDone:
    def test_false_when_not_done(self, tmp_output):
        assert is_step_done("ch_check", "is_written") is False

    def test_true_after_marking(self, tmp_output):
        mark_step_done("ch_check2", "is_video_done")
        assert is_step_done("ch_check2", "is_video_done") is True

    def test_false_for_empty_chapter_id(self):
        assert is_step_done("", "is_written") is False
