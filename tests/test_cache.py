# -*- coding: utf-8 -*-
"""Test module: cache.py - Kiểm tra disk cache decorator."""
import os
import json
import time
import pytest

from src.cache import cached, _get_cache_path, CACHE_DIR


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    """Chuyển CACHE_DIR sang thư mục tạm."""
    monkeypatch.setattr("src.cache.CACHE_DIR", str(tmp_path / "cache"))
    return tmp_path / "cache"


class TestGetCachePath:
    def test_returns_json_path(self):
        path = _get_cache_path("test_key")
        assert path.endswith(".json")

    def test_deterministic(self):
        assert _get_cache_path("abc") == _get_cache_path("abc")

    def test_different_keys_different_paths(self):
        assert _get_cache_path("a") != _get_cache_path("b")


class TestCachedDecorator:
    def test_caches_result(self):
        call_count = 0

        @cached(ttl_seconds=3600)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return f"result_{x}"

        # Lần 1: gọi thật
        result1 = expensive_func("hello")
        assert result1 == "result_hello"
        assert call_count == 1

        # Lần 2: lấy từ cache
        result2 = expensive_func("hello")
        assert result2 == "result_hello"
        assert call_count == 1  # Không gọi lại

    def test_does_not_cache_empty_result(self):
        call_count = 0

        @cached(ttl_seconds=3600)
        def return_empty():
            nonlocal call_count
            call_count += 1
            return ""

        return_empty()
        return_empty()
        assert call_count == 2  # Gọi lại vì result rỗng

    def test_does_not_cache_none_result(self):
        call_count = 0

        @cached(ttl_seconds=3600)
        def return_none():
            nonlocal call_count
            call_count += 1
            return None

        return_none()
        return_none()
        assert call_count == 2

    def test_ttl_expiry(self):
        call_count = 0

        @cached(ttl_seconds=1)
        def short_ttl():
            nonlocal call_count
            call_count += 1
            return "fresh"

        short_ttl()
        assert call_count == 1
        time.sleep(1.1)
        short_ttl()
        assert call_count == 2  # Cache hết hạn, gọi lại

    def test_different_args_separate_cache(self):
        call_count = 0

        @cached(ttl_seconds=3600)
        def func_with_args(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        func_with_args(1, 2)
        func_with_args(3, 4)
        assert call_count == 2  # Hai key khác nhau
