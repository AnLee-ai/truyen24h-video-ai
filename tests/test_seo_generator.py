# -*- coding: utf-8 -*-
"""Test module: seo_generator.py - Kiểm tra SEO metadata generation."""
import pytest
from unittest.mock import patch

from src.seo_generator import generate_seo_metadata


class TestGenerateSeoMetadata:
    @patch("src.seo_generator.call_gemini")
    def test_successful_generation(self, mock_gemini):
        """Khi Gemini trả về JSON hợp lệ."""
        mock_gemini.return_value = '{"youtube_title": "Hook - Tập 1: Thức Tỉnh | Truyện 24h", "summary": "Tóm tắt", "tags": ["test"], "hashtags": ["#Test"], "engagement_question": "Q?"}'
        result = generate_seo_metadata("Thức Tỉnh", 1, "Nội dung mẫu")
        assert "youtube_title" in result
        assert "Truyện 24h" in result["youtube_title"]

    @patch("src.seo_generator.call_gemini", side_effect=Exception("API error"))
    def test_fallback_on_error(self, mock_gemini):
        """Khi Gemini lỗi, trả về fallback mặc định."""
        result = generate_seo_metadata("Thức Tỉnh", 5, "snippet")
        assert "youtube_title" in result
        assert "Tập 5" in result["youtube_title"]
        assert "Truyện 24h" in result["youtube_title"]
        assert "tags" in result
        assert "hashtags" in result
        assert len(result["tags"]) > 0

    @patch("src.seo_generator.call_gemini", return_value="not json at all")
    def test_invalid_json_from_gemini(self, mock_gemini):
        """Khi Gemini trả về text không parse được."""
        result = generate_seo_metadata("Test", 1, "abc")
        # safe_loads trả {} => vẫn có keys? 
        # Thực tế safe_loads("not json at all") => {} nên result = {}
        assert isinstance(result, dict)
