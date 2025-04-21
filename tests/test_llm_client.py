"""
Tests for the OllamaClient class
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from src.foundation.llm_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    """Test cases for OllamaClient"""

    def setUp(self):
        """Set up for tests"""
        self.client = OllamaClient(model="test-model", ollama_url="http://test-url:11434")
        
    @patch('requests.post')
    def test_make_request_success(self, mock_post):
        """Test successful request to Ollama API"""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client._make_request("Test prompt")
        
        # Check results
        self.assertEqual(result, "Test response")
        mock_post.assert_called_once()
        
        # Extract and check payload
        call_args = mock_post.call_args[1]
        payload = call_args['json']
        self.assertEqual(payload['model'], "test-model")
        self.assertEqual(payload['prompt'], "Test prompt")
        self.assertFalse(payload['stream'])
        
    @patch('requests.post')
    def test_make_request_with_system(self, mock_post):
        """Test request with system message"""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_post.return_value = mock_response
        
        # Call method with system message
        result = self.client._make_request("Test prompt", system="System message")
        
        # Check results
        self.assertEqual(result, "Test response")
        mock_post.assert_called_once()
        
        # Extract and check payload
        call_args = mock_post.call_args[1]
        payload = call_args['json']
        self.assertEqual(payload['system'], "System message")
        
    @patch('requests.post')
    def test_make_request_error(self, mock_post):
        """Test request that returns error status code"""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client._make_request("Test prompt", max_attempts=1)
        
        # Check results
        self.assertIsNone(result)
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_get_completion(self, mock_post):
        """Test get_completion method"""
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Completion text"}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client.get_completion("Test prompt")
        
        # Check results
        self.assertEqual(result, "Completion text")
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_get_json_completion_direct_json(self, mock_post):
        """Test get_json_completion with direct valid JSON response"""
        # Valid JSON in the response
        json_response = '{"key1": "value1", "key2": 42}'
        
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": json_response}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client.get_json_completion("Test prompt")
        
        # Check results
        self.assertEqual(result, {"key1": "value1", "key2": 42})
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_get_json_completion_with_code_block(self, mock_post):
        """Test get_json_completion with JSON in code block"""
        # JSON in code block
        code_block_response = '```json\n{"key1": "value1", "key2": 42}\n```'
        
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": code_block_response}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client.get_json_completion("Test prompt")
        
        # Check results
        self.assertEqual(result, {"key1": "value1", "key2": 42})
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_get_json_completion_with_braces(self, mock_post):
        """Test get_json_completion with JSON enclosed in braces"""
        # JSON with surrounding text
        text_with_json = 'Here is the JSON response: {"key1": "value1", "key2": 42} Please let me know if you need more.'
        
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": text_with_json}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client.get_json_completion("Test prompt")
        
        # Check results
        self.assertEqual(result, {"key1": "value1", "key2": 42})
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_get_json_completion_failed_parsing(self, mock_post):
        """Test get_json_completion with invalid JSON response"""
        # Invalid JSON that can't be parsed
        invalid_json = 'This is not valid JSON: {key1: value1, key2: 42'
        
        # Configure mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": invalid_json}
        mock_post.return_value = mock_response
        
        # Call method
        result = self.client.get_json_completion("Test prompt")
        
        # Check results
        self.assertIsNone(result)
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main() 