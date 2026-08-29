# -*- coding: utf-8 -*-
"""Test module: video_validator.py - Kiểm tra validate video file."""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.video_validator import validate_video_file


@pytest.fixture
def valid_video(tmp_path):
    """Tạo file video giả đủ lớn."""
    video = tmp_path / "test.mp4"
    video.write_bytes(b"\x00" * 200000)  # 200KB
    return str(video)


@pytest.fixture
def small_video(tmp_path):
    """Tạo file video quá nhỏ."""
    video = tmp_path / "tiny.mp4"
    video.write_bytes(b"\x00" * 100)
    return str(video)


class TestValidateVideoFile:
    def test_nonexistent_file(self):
        assert validate_video_file("/nonexistent/video.mp4") is False

    def test_empty_path(self):
        assert validate_video_file("") is False

    def test_none_path(self):
        assert validate_video_file(None) is False

    def test_file_too_small(self, small_video):
        assert validate_video_file(small_video) is False

    def test_custom_min_size(self, valid_video):
        # File 200KB < 500KB custom threshold
        assert validate_video_file(valid_video, min_size_bytes=500000) is False

    @patch("subprocess.run")
    def test_valid_video_with_ffprobe(self, mock_run, valid_video):
        """Giả lập ffprobe trả về duration hợp lệ."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="120.5\n"
        )
        assert validate_video_file(valid_video) is True

    @patch("subprocess.run")
    def test_too_short_duration(self, mock_run, valid_video):
        """Video quá ngắn (< 1 giây)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0.5\n"
        )
        assert validate_video_file(valid_video) is False

    @patch("subprocess.run")
    def test_ffprobe_failure(self, mock_run, valid_video):
        """ffprobe trả về lỗi (file hỏng)."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=""
        )
        assert validate_video_file(valid_video) is False

    @patch("subprocess.run", side_effect=FileNotFoundError("ffprobe not found"))
    def test_ffprobe_not_installed_fallback(self, mock_run, tmp_path):
        """Khi ffprobe không có, fallback sang kiểm tra size."""
        # File > 5MB => True
        big = tmp_path / "big.mp4"
        big.write_bytes(b"\x00" * 6000000)
        assert validate_video_file(str(big)) is True

        # File < 5MB => False
        small = tmp_path / "small2.mp4"
        small.write_bytes(b"\x00" * 200000)
        assert validate_video_file(str(small)) is False

    @patch("subprocess.run", side_effect=Exception("timeout"))
    def test_ffprobe_timeout_fallback(self, mock_run, tmp_path):
        """Khi ffprobe timeout."""
        big = tmp_path / "timeout.mp4"
        big.write_bytes(b"\x00" * 6000000)
        assert validate_video_file(str(big)) is True
