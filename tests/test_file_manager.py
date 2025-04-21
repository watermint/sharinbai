"""
Tests for the FileManager class
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.content.file_manager import FileManager


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager"""

    def setUp(self):
        """Set up for tests"""
        self.file_manager = FileManager()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_path(self):
        """Test sanitize_path method"""
        test_cases = [
            # Input, Expected Output
            ("normal_path", "normal_path"),
            ("path/with/slash", "path/with/slash"),
            ("path with spaces", "path with spaces"),
            ("path<with>invalid:chars|?*", "path_with_invalid_chars___"),  # 3 underscores for 3 replaced chars
            ("path with trailing spaces  ", "path with trailing spaces"),
            ("path with trailing dots...", "path with trailing dots"),
            ("path  with   multiple    spaces", "path with multiple spaces"),
        ]

        for input_path, expected_output in test_cases:
            self.assertEqual(
                self.file_manager.sanitize_path(input_path),
                expected_output,
                f"Failed to sanitize {input_path} correctly"
            )

    def test_ensure_directory(self):
        """Test ensure_directory method"""
        test_dir = os.path.join(self.temp_dir, "test_dir")
        
        # Directory doesn't exist yet
        self.assertFalse(os.path.exists(test_dir))
        
        # Create directory
        result = self.file_manager.ensure_directory(test_dir)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_dir))
        
        # Try creating existing directory
        result = self.file_manager.ensure_directory(test_dir)
        self.assertTrue(result)

    def test_write_and_read_text_file(self):
        """Test write_text_file and read_text_file methods"""
        test_file = os.path.join(self.temp_dir, "test_file.txt")
        test_content = "This is test content."
        
        # Write file
        write_result = self.file_manager.write_text_file(test_file, test_content)
        self.assertTrue(write_result)
        self.assertTrue(os.path.exists(test_file))
        
        # Read file
        read_content = self.file_manager.read_text_file(test_file)
        self.assertEqual(read_content, test_content)
        
        # Test reading non-existent file
        non_existent_file = os.path.join(self.temp_dir, "non_existent.txt")
        read_content = self.file_manager.read_text_file(non_existent_file)
        self.assertIsNone(read_content)

    def test_file_exists(self):
        """Test file_exists method"""
        test_file = os.path.join(self.temp_dir, "exists_test.txt")
        
        # File doesn't exist yet
        self.assertFalse(self.file_manager.file_exists(test_file))
        
        # Create file
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # File should exist now
        self.assertTrue(self.file_manager.file_exists(test_file))

    def test_create_path(self):
        """Test create_path method"""
        base_dir = "/base/dir"
        parts = ["part1", "part2", "file.txt"]
        
        expected_path = os.path.join(base_dir, "part1", "part2", "file.txt")
        result_path = self.file_manager.create_path(base_dir, *parts)
        
        self.assertEqual(result_path, expected_path)
        
        # Test with sanitization
        parts_with_invalid_chars = ["part<1>", "part:2|", "file?.txt*"]
        expected_sanitized_path = os.path.join(base_dir, "part_1_", "part_2_", "file_.txt_")
        result_path = self.file_manager.create_path(base_dir, *parts_with_invalid_chars)
        
        self.assertEqual(result_path, expected_sanitized_path)


if __name__ == "__main__":
    unittest.main() 