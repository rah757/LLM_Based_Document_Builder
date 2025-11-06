"""
Tests for placeholder detection and processing
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.placeholder_utils import detect_placeholders, extract_context


class TestPlaceholderDetection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_text = """
        This is a sample SAFE agreement between [Company Name] and [Investor Name].
        The investment amount is ${{Purchase Amount}} as of {Date of Safe}.
        """
        
        self.patterns_config = {
            "patterns": [
                {
                    "name": "square_brackets",
                    "regex": "\\[([A-Za-z0-9\\s_\\-]+)\\]",
                    "enabled": True
                },
                {
                    "name": "double_curly_braces",
                    "regex": "\\{\\{([A-Za-z0-9\\s_\\-]+)\\}\\}",
                    "enabled": True
                },
                {
                    "name": "single_curly_braces",
                    "regex": "\\{([A-Za-z0-9\\s_\\-]+)\\}",
                    "enabled": True
                }
            ],
            "context_words_count": 20
        }
    
    def test_detect_square_brackets(self):
        """Test detection of [placeholder] format"""
        placeholders = detect_placeholders(self.test_text, self.patterns_config)
        
        # Should detect [Company Name] and [Investor Name]
        square_placeholders = [p for p in placeholders if p['pattern_type'] == 'square_brackets']
        self.assertEqual(len(square_placeholders), 2)
        
        names = [p['placeholder_name'] for p in square_placeholders]
        self.assertIn('Company Name', names)
        self.assertIn('Investor Name', names)
    
    def test_extract_context(self):
        """Test context extraction around placeholders"""
        text = "This is some text before [Placeholder] and this is text after."
        start_pos = text.index('[Placeholder]')
        end_pos = start_pos + len('[Placeholder]')
        
        before, after, before_count, after_count = extract_context(text, start_pos, end_pos, 5)
        
        self.assertTrue('before' in before.lower())
        self.assertTrue('after' in after.lower())
        self.assertGreater(before_count, 0)
        self.assertGreater(after_count, 0)


if __name__ == '__main__':
    unittest.main()

