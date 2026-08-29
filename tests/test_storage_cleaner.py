# -*- coding: utf-8 -*-
"""Test module: storage_cleaner.py - Kiểm tra dọn dẹp file tạm."""
import os
import pytest

from src.storage_cleaner import cleanup_temporary_artifacts


@pytest.fixture
def chapter_dir(tmp_path, monkeypatch):
    """Tạo cấu trúc thư mục output/chapter giả."""
    monkeypatch.chdir(tmp_path)
    ch_dir = tmp_path / "output" / "ch_test"
    images_dir = ch_dir / "images"
    images_dir.mkdir(parents=True)
    # Tạo file giả
    (images_dir / "scene_001.jpg").write_bytes(b"fake_img")
    (images_dir / "scene_002.jpg").write_bytes(b"fake_img")
    (images_dir / "final.mp4").write_bytes(b"fake_video")
    (ch_dir / "concat_list.txt").write_text("file1\nfile2")
    return tmp_path


class TestCleanupTemporaryArtifacts:
    def test_keep_video_removes_non_mp4(self, chapter_dir):
        cleanup_temporary_artifacts("ch_test", keep_video=True)
        images_dir = chapter_dir / "output" / "ch_test" / "images"
        remaining = list(images_dir.iterdir())
        # Chỉ giữ lại .mp4
        assert all(f.suffix == ".mp4" for f in remaining)
        assert len(remaining) == 1

    def test_keep_video_removes_concat_list(self, chapter_dir):
        cleanup_temporary_artifacts("ch_test", keep_video=True)
        assert not (chapter_dir / "output" / "ch_test" / "concat_list.txt").exists()

    def test_no_keep_video_removes_images_dir(self, chapter_dir):
        cleanup_temporary_artifacts("ch_test", keep_video=False)
        assert not (chapter_dir / "output" / "ch_test" / "images").exists()

    def test_nonexistent_chapter_no_error(self, chapter_dir):
        # Không crash khi chapter không tồn tại
        cleanup_temporary_artifacts("nonexistent", keep_video=True)

    def test_no_images_dir_no_error(self, chapter_dir):
        import shutil
        shutil.rmtree(chapter_dir / "output" / "ch_test" / "images")
        cleanup_temporary_artifacts("ch_test", keep_video=True)
