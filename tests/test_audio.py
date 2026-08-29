# -*- coding: utf-8 -*-
"""Test module: audio.py - Kiểm tra mix BGM với voice (mock pydub)."""
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from src.audio import mix_bgm_with_voice


@pytest.fixture
def voice_file(tmp_path):
    """Tạo file voice giả."""
    voice = tmp_path / "voice.mp3"
    voice.write_bytes(b"\x00" * 1000)
    return str(voice)


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Mock config dirs."""
    monkeypatch.setattr("src.audio.config.OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setattr("src.audio.config.BGM_DIR", str(tmp_path / "bgm"))
    os.makedirs(tmp_path / "output", exist_ok=True)
    return tmp_path


class TestMixBgmWithVoice:
    def test_missing_voice_file(self, setup_dirs):
        result = mix_bgm_with_voice("/nonexistent/voice.mp3", "ch01")
        assert result == ""

    @patch("src.audio.AudioSegment.from_mp3")
    @patch("src.audio.normalize")
    def test_no_bgm_exports_voice_only(self, mock_normalize, mock_from_mp3, voice_file, setup_dirs):
        """Khi không có file BGM, export voice nguyên bản."""
        mock_voice = MagicMock()
        mock_voice.export = MagicMock()
        mock_from_mp3.return_value = mock_voice
        mock_normalize.return_value = mock_voice

        result = mix_bgm_with_voice(voice_file, "ch01")
        mock_voice.export.assert_called_once()

    @patch("src.audio.AudioSegment.from_file")
    @patch("src.audio.AudioSegment.from_mp3")
    @patch("src.audio.normalize")
    def test_mix_with_bgm(self, mock_normalize, mock_from_mp3, mock_from_file, voice_file, setup_dirs):
        """Khi có file BGM, overlay và export."""
        # Tạo file BGM giả
        bgm_dir = setup_dirs / "bgm"
        os.makedirs(bgm_dir, exist_ok=True)
        (bgm_dir / "bg.mp3").write_bytes(b"\x00" * 500)

        mock_voice = MagicMock()
        mock_voice.dbfs = -15.0
        mock_voice.__len__ = lambda self: 10000
        mock_voice.overlay = MagicMock(return_value=mock_voice)
        mock_from_mp3.return_value = mock_voice
        mock_normalize.return_value = mock_voice

        mock_bgm = MagicMock()
        mock_bgm.dbfs = -20.0
        mock_bgm.__len__ = lambda self: 5000
        mock_bgm.__sub__ = lambda self, x: self
        mock_bgm.__mul__ = lambda self, x: self
        mock_bgm.__getitem__ = lambda self, x: self
        mock_bgm.fade_out = MagicMock(return_value=mock_bgm)
        mock_from_file.return_value = mock_bgm

        result = mix_bgm_with_voice(voice_file, "ch_bgm")
        mock_voice.overlay.assert_called_once()

    @patch("src.audio.AudioSegment.from_mp3", side_effect=Exception("decode error"))
    def test_fallback_on_decode_error(self, mock_from_mp3, voice_file, setup_dirs):
        """Khi pydub lỗi, fallback copy file nguyên bản."""
        result = mix_bgm_with_voice(voice_file, "ch_err")
        # Nên trả về path (fallback copy hoặc original)
        assert result != ""
