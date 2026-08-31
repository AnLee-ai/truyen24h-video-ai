import os
import sys
import unittest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src import thumbnail_generator

class TestThumbnailGenerator(unittest.TestCase):

    def setUp(self):
        self.output_path = "output/test_thumbnail_gen.jpg"

    def tearDown(self):
        if os.path.exists(self.output_path):
            try:
                os.remove(self.output_path)
            except Exception:
                pass

    def test_generate_youtube_thumbnail_fallback_canvas(self):
        """Test thumbnail generation creates a valid 16:9 1920x1080 image even with non-existent scene_image_path."""
        fake_scene = os.path.join(self.test_dir, "non_existent_folder", "fake_scene.jpg")
        result = thumbnail_generator.generate_youtube_thumbnail(
            chapter_num=8,
            chapter_title="Trận Đấu Khốc Liệt",
            scene_image_path=fake_scene,
            output_path=self.output_path,
            width=1920,
            height=1080
        )
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 10000)
        
        with Image.open(result) as img:
            self.assertEqual(img.size, (1920, 1080))
            self.assertEqual(img.mode, "RGB")

if __name__ == "__main__":
    unittest.main()
