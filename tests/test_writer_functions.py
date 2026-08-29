# -*- coding: utf-8 -*-
"""Test module: writer.py - Kiểm tra các hàm xử lý text thuần (không gọi API)."""
import pytest

from src.writer import (
    safe_loads,
    remove_repetitive_sentences,
    clean_chapter_content,
    verify_and_sanitize_chapter_content,
    safe_print,
)


class TestSafeLoads:
    def test_valid_json(self):
        assert safe_loads('{"a": 1}') == {"a": 1}

    def test_json_in_code_block(self):
        text = '```json\n{"key": "val"}\n```'
        assert safe_loads(text) == {"key": "val"}

    def test_json_in_code_block_no_lang(self):
        text = '```\n{"key": "val"}\n```'
        assert safe_loads(text) == {"key": "val"}

    def test_trailing_comma(self):
        text = '{"a": 1, "b": 2,}'
        result = safe_loads(text)
        assert result == {"a": 1, "b": 2}

    def test_empty_string(self):
        assert safe_loads("") == {}

    def test_none_input(self):
        assert safe_loads(None) == {}

    def test_whitespace_only(self):
        assert safe_loads("   ") == {}

    def test_default_value(self):
        assert safe_loads("invalid", default=[]) == []

    def test_json_array(self):
        assert safe_loads("[1, 2, 3]") == [1, 2, 3]

    def test_json_embedded_in_text(self):
        text = 'Here is data: {"x": 99} end.'
        result = safe_loads(text)
        assert result == {"x": 99}

    def test_nested_json(self):
        text = '{"outer": {"inner": [1,2]}}'
        result = safe_loads(text)
        assert result["outer"]["inner"] == [1, 2]


class TestRemoveRepetitiveSentences:
    def test_removes_duplicate_sentences(self):
        text = "Hắn nổi giận. Hắn nổi giận. Nhưng rồi hắn bình tĩnh."
        result = remove_repetitive_sentences(text)
        assert result.count("Hắn nổi giận.") == 1

    def test_removes_duplicate_paragraphs(self):
        text = "Dòng A\nDòng A\nDòng B"
        result = remove_repetitive_sentences(text)
        lines = [l for l in result.split("\n") if l.strip()]
        assert lines == ["Dòng A", "Dòng B"]

    def test_preserves_different_content(self):
        text = "Câu 1. Câu 2. Câu 3."
        result = remove_repetitive_sentences(text)
        assert "Câu 1" in result
        assert "Câu 2" in result
        assert "Câu 3" in result

    def test_empty_input(self):
        assert remove_repetitive_sentences("") == ""

    def test_collapses_multiple_blank_lines(self):
        text = "A\n\n\n\nB"
        result = remove_repetitive_sentences(text)
        assert "\n\n\n" not in result


class TestCleanChapterContent:
    def test_removes_prologue_prefix(self):
        text = "Dẫn lược: Đây là câu chuyện hay."
        result = clean_chapter_content(text)
        assert not result.startswith("Dẫn lược")

    def test_removes_introduction_prefix(self):
        text = "Giới thiệu: Nhân vật chính là..."
        result = clean_chapter_content(text)
        assert not result.startswith("Giới thiệu")

    def test_strips_whitespace(self):
        text = "   \n  Nội dung truyện.  \n  "
        result = clean_chapter_content(text)
        assert result == "Nội dung truyện."

    def test_removes_markdown_bold_prefix(self):
        text = "**Dẫn lược**: Nội dung bắt đầu."
        result = clean_chapter_content(text)
        assert "Dẫn lược" not in result or "Nội dung bắt đầu" in result


class TestVerifyAndSanitize:
    def test_empty_text(self):
        text, changed = verify_and_sanitize_chapter_content("")
        assert text == ""
        assert changed is False

    def test_none_text(self):
        text, changed = verify_and_sanitize_chapter_content(None)
        assert text is None
        assert changed is False

    def test_clean_text_unchanged(self):
        original = "Tiêu Viêm nhìn ra xa. Hắn cảm nhận sức mạnh dồi dào."
        text, changed = verify_and_sanitize_chapter_content(original)
        assert text == original
        assert changed is False


class TestSafePrint:
    def test_normal_string(self, capsys):
        safe_print("Hello World")
        captured = capsys.readouterr()
        assert "Hello World" in captured.out

    def test_unicode_string(self, capsys):
        safe_print("Tiêu Viêm ✅")
        captured = capsys.readouterr()
        assert "Tiêu Viêm" in captured.out
