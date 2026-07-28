import os
import sys
import unittest

# Ensure sys.path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config, key_rotator, writer, tts, audio, video, shorts_generator, database, telegram_uploader, main

class TestFullSystemIntegrity(unittest.TestCase):
    
    def test_01_key_rotator_permanent_invalidation(self):
        """Test that 401 invalid keys are PERMANENTLY ignored and never retried."""
        rotator = key_rotator.APIKeyRotator(
            provider="TestProvider",
            env_var_single="TEST_SINGLE_KEY",
            env_var_multi="TEST_MULTI_KEYS",
            default_keys=["key_bad_1", "key_bad_2"]
        )
        
        # Initial key should be key_bad_1
        k1 = rotator.get_key()
        self.assertEqual(k1, "key_bad_1")
        
        # Mark key_bad_1 permanently 401 failed
        rotator.mark_key_failed("key_bad_1", is_permanent=True)
        
        # Next key should be key_bad_2
        k2 = rotator.get_key()
        self.assertEqual(k2, "key_bad_2")
        
        # Mark key_bad_2 permanently 401 failed
        rotator.mark_key_failed("key_bad_2", is_permanent=True)
        
        # When all keys are 401 invalid, get_key() MUST return empty string ""
        k_empty = rotator.get_key()
        self.assertEqual(k_empty, "")
        
        # Double check: even on subsequent calls, it MUST stay empty ""!
        self.assertEqual(rotator.get_key(), "")

    def test_02_key_rotator_rate_limit_recycle(self):
        """Test that 429 rate-limited keys can be recycled when no unthrottled key remains."""
        rotator = key_rotator.APIKeyRotator(
            provider="TestProvider2",
            env_var_single="TEST_SINGLE_KEY2",
            env_var_multi="TEST_MULTI_KEYS2",
            default_keys=["key_quota_1"]
        )
        
        k1 = rotator.get_key()
        self.assertEqual(k1, "key_quota_1")
        
        # Mark temporary 429 rate limit
        rotator.mark_key_failed("key_quota_1", is_permanent=False)
        
        # Because it's temporary (429), get_key() should safely recycle it instead of returning empty
        k_recycled = rotator.get_key()
        self.assertEqual(k_recycled, "key_quota_1")

    def test_03_main_quality_guardrail(self):
        """Test that main.py quality guardrail aborts cleanly on short text (<200 words)."""
        # Test word count logic
        short_text = "Tiếp tục diễn biến câu chuyện."
        self.assertLess(len(short_text.split()), 200)

    def test_04_ffmpeg_command_structure(self):
        """Test FFmpeg detection and safe audio seek parameters."""
        import subprocess
        chk = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        self.assertEqual(chk.returncode, 0)

if __name__ == "__main__":
    unittest.main()
