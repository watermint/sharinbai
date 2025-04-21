"""
Tests for the ContentGenerator class
"""

import datetime
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.content.content_generator import ContentGenerator


class TestContentGenerator(unittest.TestCase):
    """Test cases for ContentGenerator"""
    
    def setUp(self):
        """Set up for tests"""
        # Create a temporary directory for test output
        self.temp_dir = tempfile.mkdtemp()
        
        # Set up mocks
        self.mock_llm_client = MagicMock()
        self.mock_file_manager = MagicMock()
        self.mock_text_generator = MagicMock()
        self.mock_docx_generator = MagicMock()
        self.mock_pdf_generator = MagicMock()
        self.mock_xlsx_generator = MagicMock()
        self.mock_image_generator = MagicMock()
        
        # Set up patchers
        self.ollama_patcher = patch('src.foundation.llm_client.OllamaClient', return_value=self.mock_llm_client)
        self.file_manager_patcher = patch('src.content.file_manager.FileManager', return_value=self.mock_file_manager)
        self.text_generator_patcher = patch('src.content.generators.TextGenerator', return_value=self.mock_text_generator)
        self.docx_generator_patcher = patch('src.content.generators.DocxGenerator', return_value=self.mock_docx_generator)
        self.pdf_generator_patcher = patch('src.content.generators.PdfGenerator', return_value=self.mock_pdf_generator)
        self.xlsx_generator_patcher = patch('src.content.generators.XlsxGenerator', return_value=self.mock_xlsx_generator)
        self.image_generator_patcher = patch('src.content.generators.ImageGenerator', return_value=self.mock_image_generator)
        
        # Start patchers
        self.ollama_patcher.start()
        self.file_manager_patcher.start()
        self.text_generator_patcher.start()
        self.docx_generator_patcher.start()
        self.pdf_generator_patcher.start()
        self.xlsx_generator_patcher.start()
        self.image_generator_patcher.start()
        
        # Set up common mock behaviors
        self.mock_file_manager.ensure_directory.return_value = True
        self.mock_file_manager.write_json_file.return_value = True
        
        # Initialize test subject
        self.content_generator = ContentGenerator(model="test-model", ollama_url="http://test-url:11434")
        
    def tearDown(self):
        """Clean up after tests"""
        # Stop patchers
        self.ollama_patcher.stop()
        self.file_manager_patcher.stop()
        self.text_generator_patcher.stop()
        self.docx_generator_patcher.stop()
        self.pdf_generator_patcher.stop()
        self.xlsx_generator_patcher.stop()
        self.image_generator_patcher.stop()
        
    def test_initialization(self):
        """Test ContentGenerator initialization"""
        self.assertEqual(self.content_generator.llm_client, self.mock_llm_client)
        self.assertEqual(self.content_generator.file_manager, self.mock_file_manager)
        self.assertEqual(len(self.content_generator.generators), 5)
        self.assertIn("txt", self.content_generator.generators)
        self.assertIn("docx", self.content_generator.generators)
        self.assertIn("pdf", self.content_generator.generators)
        self.assertIn("xlsx", self.content_generator.generators)
        self.assertIn("image", self.content_generator.generators)
        
    def test_generate_file_without_purpose(self):
        """Test generate_file method without purpose attribute"""
        # Configure mocks
        self.mock_text_generator.generate.return_value = True
        
        # Call method
        result = self.content_generator.generate_file(
            self.temp_dir, "test.txt", "Test file", "healthcare", "en", "doctor"
        )
        
        # Verify results
        self.assertTrue(result)
        self.mock_file_manager.ensure_directory.assert_called_once_with(self.temp_dir)
        self.mock_file_manager.write_json_file.assert_called_once()
        self.mock_text_generator.generate.assert_called_once_with(
            self.temp_dir, "test.txt", "Test file", "healthcare", "en", "doctor"
        )
        
    def test_generate_file_with_timeseries_purpose(self):
        """Test generate_file method with timeseries purpose"""
        # Configure mocks
        self.mock_text_generator.generate.return_value = True
        
        # Patch datetime to return a fixed date
        fixed_date = datetime.datetime(2023, 1, 15)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            
            # Call method
            result = self.content_generator.generate_file(
                self.temp_dir, "report.txt", "Daily report", "healthcare", "en", "doctor", purpose="timeseries"
            )
            
            # Verify results
            self.assertTrue(result)
            self.mock_file_manager.ensure_directory.assert_called_once_with(self.temp_dir)
            self.mock_file_manager.write_json_file.assert_called_once()
            
            # Check that date prefix was added to filename
            expected_filename = "2023-01-15_report.txt"
            self.mock_text_generator.generate.assert_called_once_with(
                self.temp_dir, expected_filename, "Daily report", "healthcare", "en", "doctor"
            )
            
    def test_format_timeseries_filename(self):
        """Test _format_timeseries_filename method"""
        # Patch datetime to return a fixed date
        fixed_date = datetime.datetime(2023, 1, 15)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            
            # Test with regular filename
            result = self.content_generator._format_timeseries_filename("report.txt", "txt")
            self.assertEqual(result, "2023-01-15_report.txt")
            
            # Test with filename that already has date prefix
            result = self.content_generator._format_timeseries_filename("2023-01-15_report.txt", "txt")
            self.assertEqual(result, "2023-01-15_report.txt")
            
    def test_is_timeseries_limit_reached(self):
        """Test is_timeseries_limit_reached method"""
        # Mock directory structure with timeseries folders
        mock_folders = ["folder1", "folder2", "folder3"]
        mock_metadata = {
            "folder1": {"purpose": "timeseries"},
            "folder2": {"purpose": "timeseries"},
            "folder3": {"purpose": "general"}
        }
        
        with patch('os.listdir', return_value=mock_folders), \
             patch('os.path.isdir', return_value=True), \
             patch('os.path.exists', return_value=True), \
             patch.object(self.mock_file_manager, 'read_json_file', 
                         side_effect=lambda path: mock_metadata.get(os.path.basename(os.path.dirname(path)))):
            
            # Test with 2 timeseries folders (below limit)
            self.assertFalse(self.content_generator.is_timeseries_limit_reached("/test/path"))
            
            # Change the limit temporarily to test the limit reached case
            original_limit = self.content_generator.MAX_TIMESERIES_FOLDERS
            self.content_generator.MAX_TIMESERIES_FOLDERS = 2
            
            # Test with 2 timeseries folders (at limit)
            self.assertTrue(self.content_generator.is_timeseries_limit_reached("/test/path"))
            
            # Restore original limit
            self.content_generator.MAX_TIMESERIES_FOLDERS = original_limit
            
    def test_generate_file_with_unknown_extension(self):
        """Test generate_file method with unknown extension"""
        # Configure mocks
        self.mock_text_generator.generate.return_value = True
        
        # Call method with unknown extension
        result = self.content_generator.generate_file(
            self.temp_dir, "test.xyz", "Test file with unknown extension", "healthcare", "en", "doctor"
        )
        
        # Verify results
        self.assertTrue(result)
        self.mock_file_manager.ensure_directory.assert_called_once_with(self.temp_dir)
        self.mock_file_manager.write_json_file.assert_called_once()
        
        # Check that text generator was used as fallback
        self.mock_text_generator.generate.assert_called_once()
        
    def test_generate_file_with_image_extension(self):
        """Test generate_file method with image extension"""
        # Configure mocks
        self.mock_image_generator.generate.return_value = True
        
        # Call method with image extension
        result = self.content_generator.generate_file(
            self.temp_dir, "test.png", "Test image", "healthcare", "en", "doctor"
        )
        
        # Verify results
        self.assertTrue(result)
        self.mock_file_manager.ensure_directory.assert_called_once_with(self.temp_dir)
        self.mock_file_manager.write_json_file.assert_called_once()
        
        # Check that image generator was used
        self.mock_image_generator.generate.assert_called_once()

if __name__ == '__main__':
    unittest.main() 