import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src import config

class TestConfig(unittest.TestCase):
    
    def test_paths_exist(self):
        self.assertIsNotNone(config.BASE_DIR)
        self.assertIsNotNone(config.SRC_DIR)
        self.assertIsNotNone(config.DATA_DIR)
        self.assertIsNotNone(config.OUTPUT_DIR)
        self.assertIsNotNone(config.BGM_DIR)
        
    def test_validate_config_returns_bool(self):
        # Result should be either True or False
        result = config.validate_config()
        self.assertIn(result, [True, False])

if __name__ == '__main__':
    unittest.main()
