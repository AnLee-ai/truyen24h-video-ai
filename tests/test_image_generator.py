# -*- coding: utf-8 -*-
"""Test module: image_generator.py - Kiểm tra image validation và fallback engine."""
import os
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from src.image_generator import is_valid_image_file, generate_scene_image


@pytest.fixture
def valid_image(tmp_path):
    """Tạo ảnh JPEG hợp lệ > 5KB."""
    img_path = tmp_path / "valid.jpg"
    import numpy as np
    # Ảnh noise để JPEG không nén quá nhỏ
    arr = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    img.save(str(img_path), "JPEG", quality=95)
    return str(img_path)


@pytest.fixture
def tiny_file(tmp_path):
    """File quá nhỏ (< 5KB)."""
    f = tmp_path / "tiny.jpg"
    f.write_bytes(b"\x00" * 100)
    return str(f)


class TestIsValidImageFile:
    def test_nonexistent(self):
        assert is_valid_image_file("/no/such/file.jpg") is False

    def test_too_small(self, tiny_file):
        assert is_valid_image_file(tiny_file) is False

    def test_valid_image(self, valid_image):
        assert is_valid_image_file(valid_image) is True

    def test_corrupt_image(self, tmp_path):
        corrupt = tmp_path / "corrupt.jpg"
        corrupt.write_bytes(b"this is not an image" * 500)
        assert is_valid_image_file(str(corrupt)) is False


class TestGenerateSceneImage:
    @patch("src.image_generator.call_huggingface_space", return_value=False)
    @patch("src.image_generator.call_colab_webhook", return_value=False)
    def test_fallback_to_procedural(self, mock_colab, mock_hf, tmp_path):
        """Khi tất cả engine thất bại, fallback procedural canvas."""
        output = str(tmp_path / "fallback.jpg")
        with patch("urllib.request.urlopen", side_effect=Exception("network")):
            result = generate_scene_image("Tiêu Viêm cầm hỏa kiếm", output, width=800, height=600)
        assert os.path.exists(result)
        assert is_valid_image_file(result)

    def test_skips_existing_valid_image(self, valid_image):
        """Không tạo lại nếu ảnh đã tồn tại và hợp lệ."""
        result = generate_scene_image("any prompt", valid_image)
        assert result == valid_image

    @patch("src.image_generator.call_huggingface_space", return_value=False)
    @patch("src.image_generator.call_colab_webhook", return_value=False)
    def test_deterministic_seed(self, mock_colab, mock_hf, tmp_path):
        """Seed cố định cho kết quả tái tạo được."""
        out1 = str(tmp_path / "s1.jpg")
        out2 = str(tmp_path / "s2.jpg")
        with patch("urllib.request.urlopen", side_effect=Exception("net")):
            generate_scene_image("test", out1, width=50, height=50, seed=42)
            generate_scene_image("test", out2, width=50, height=50, seed=42)
        # Cùng seed, cùng procedural output
        assert os.path.getsize(out1) > 0
        assert os.path.getsize(out2) > 0
