import unittest
import sys
import os

# Add src to python path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tts import vtt_to_srt

class TestTTSConversion(unittest.TestCase):
    
    def test_vtt_to_srt_basic(self):
        vtt_content = """WEBVTT

00:00:01.230 --> 00:00:03.450
Hello World

00:00:04.000 --> 00:00:06.100
Second Line of text
"""
        expected_srt = """1
00:00:01,230 --> 00:00:03,450
Hello World

2
00:00:04,000 --> 00:00:06,100
Second Line of text"""
        
        result = vtt_to_srt(vtt_content)
        self.assertEqual(result.strip(), expected_srt.strip())

    def test_vtt_to_srt_empty(self):
        vtt_content = "WEBVTT\n"
        result = vtt_to_srt(vtt_content)
        self.assertEqual(result.strip(), "")

    def test_vtt_to_srt_diacritics(self):
        # Test preserving Vietnamese accents
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:02.500
Xin chào các bạn, đây là Truyện 24h Audio.
"""
        expected_srt = """1
00:00:01,000 --> 00:00:02,500
Xin chào các bạn, đây là Truyện 24h Audio."""
        
        result = vtt_to_srt(vtt_content)
        self.assertEqual(result.strip(), expected_srt.strip())

if __name__ == '__main__':
    unittest.main()
