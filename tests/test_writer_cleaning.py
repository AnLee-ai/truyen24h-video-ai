import unittest
import sys
import os

# Add src to python path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.writer import remove_repetitive_sentences, clean_chapter_content

class TestWriterCleaning(unittest.TestCase):
    
    def test_remove_repetitive_sentences_consecutive_dup(self):
        text = "Trần Lam đi qua. Trần Lam đi qua. Cậu cảm thấy mỏi mắt."
        expected = "Trần Lam đi qua. Cậu cảm thấy mỏi mắt."
        result = remove_repetitive_sentences(text)
        self.assertEqual(result.strip(), expected.strip())
        
    def test_remove_repetitive_sentences_case_insensitive(self):
        text = "Trần Lam đi qua. trần lam đi qua. Cậu cảm thấy mỏi mắt."
        expected = "Trần Lam đi qua. Cậu cảm thấy mỏi mắt."
        result = remove_repetitive_sentences(text)
        self.assertEqual(result.strip(), expected.strip())

    def test_remove_repetitive_paragraphs(self):
        text = "Đoạn văn thứ nhất.\n\nĐoạn văn thứ nhất.\n\nĐoạn văn thứ hai."
        expected = "Đoạn văn thứ nhất.\n\nĐoạn văn thứ hai."
        result = remove_repetitive_sentences(text)
        self.assertEqual(result.strip(), expected.strip())

    def test_clean_chapter_content_prologue_labels(self):
        # Test case 1: **Dẫn lược:** prefix
        text = "**Dẫn lược:** Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        expected = "Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        self.assertEqual(clean_chapter_content(text), expected)

        # Test case 2: *Prologue:* prefix
        text = "*Prologue:* Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        expected = "Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        self.assertEqual(clean_chapter_content(text), expected)

        # Test case 3: Dẫn lược: prefix without markdown
        text = "Dẫn lược: Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        expected = "Trong một thế giới thần bí...\n\nChương 1: Trước Giờ Khai Mạc."
        self.assertEqual(clean_chapter_content(text), expected)

if __name__ == '__main__':
    unittest.main()
