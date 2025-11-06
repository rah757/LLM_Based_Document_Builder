"""
Tests for Flask API endpoints
"""

import unittest
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import app


class TestEndpoints(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_index_endpoint(self):
        """Test index page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_patterns_endpoint(self):
        """Test patterns configuration endpoint"""
        response = self.client.get('/patterns')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('patterns', data)
        self.assertIn('context_words_count', data)
    
    def test_upload_no_file(self):
        """Test upload endpoint with no file"""
        response = self.client.post('/upload')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()

