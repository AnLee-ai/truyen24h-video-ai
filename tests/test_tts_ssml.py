import unittest
import sys
import os

# Add src to python path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tts import sanitize_voice_name

class TestTTSSsml(unittest.TestCase):
    
    def test_sanitize_voice_name_short(self):
        # Short name should be preserved
        voice = "vi-VN-HoaiMyNeural"
        result = sanitize_voice_name(voice)
        self.assertEqual(result, "vi-VN-HoaiMyNeural")
        
    def test_sanitize_voice_name_long(self):
        # Long Microsoft Azure name should be correctly sanitized to short name
        long_voice = "Microsoft Server Speech Text to Speech Voice (vi-VN, HoaiMyNeural)"
        result = sanitize_voice_name(long_voice)
        self.assertEqual(result, "vi-VN-HoaiMyNeural")

if __name__ == '__main__':
    unittest.main()
