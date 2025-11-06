"""
Tests for validation utilities
"""

import unittest
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.validation_utils import determine_expected_type, validate_input_format, normalize_input


class TestValidation(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'expected_type_map.json')
        with open(config_path, 'r') as f:
            self.type_map_config = json.load(f)
    
    def test_determine_type_date(self):
        """Test type determination for date placeholders"""
        result = determine_expected_type("Date of Safe", self.type_map_config)
        self.assertEqual(result, "date")
        
        result = determine_expected_type("Effective Date", self.type_map_config)
        self.assertEqual(result, "date")
    
    def test_determine_type_email(self):
        """Test type determination for email placeholders"""
        result = determine_expected_type("Contact Email", self.type_map_config)
        self.assertEqual(result, "email")
    
    def test_determine_type_amount(self):
        """Test type determination for amount placeholders"""
        result = determine_expected_type("Purchase Amount", self.type_map_config)
        self.assertEqual(result, "amount")
        
        result = determine_expected_type("Investment Amount", self.type_map_config)
        self.assertEqual(result, "amount")
    
    def test_validate_date_format(self):
        """Test date format validation"""
        # Valid dates
        result = validate_input_format("01/15/2024", "date", self.type_map_config)
        self.assertTrue(result['valid'])
        
        result = validate_input_format("2024-01-15", "date", self.type_map_config)
        self.assertTrue(result['valid'])
        
        # Invalid date
        result = validate_input_format("January 15, 2024", "date", self.type_map_config)
        self.assertFalse(result['valid'])
    
    def test_validate_email_format(self):
        """Test email format validation"""
        # Valid email
        result = validate_input_format("user@example.com", "email", self.type_map_config)
        self.assertTrue(result['valid'])
        
        # Invalid email
        result = validate_input_format("not-an-email", "email", self.type_map_config)
        self.assertFalse(result['valid'])
    
    def test_normalize_email(self):
        """Test email normalization"""
        result = normalize_input("User@Example.COM", "email")
        self.assertEqual(result, "user@example.com")
    
    def test_normalize_percentage(self):
        """Test percentage normalization"""
        result = normalize_input("15", "percentage")
        self.assertEqual(result, "15%")
        
        result = normalize_input("15%", "percentage")
        self.assertEqual(result, "15%")


if __name__ == '__main__':
    unittest.main()

