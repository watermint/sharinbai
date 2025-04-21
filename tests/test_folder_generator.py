"""
Tests for the FolderGenerator class
"""

import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call

# Patch the classes before importing FolderGenerator
mock_llm_client = MagicMock()
mock_file_manager = MagicMock()
mock_content_generator = MagicMock()

with patch('src.foundation.llm_client.OllamaClient', return_value=mock_llm_client), \
     patch('src.content.file_manager.FileManager', return_value=mock_file_manager), \
     patch('src.content.content_generator.ContentGenerator', return_value=mock_content_generator):
    from src.structure.folder_generator import FolderGenerator


class TestFolderGenerator(unittest.TestCase):
    """Test cases for FolderGenerator"""
    
    def setUp(self):
        """Set up for tests"""
        # Create a temporary directory for test output
        self.temp_dir = tempfile.mkdtemp()
        
        # Set up test mocks
        self.mock_llm_client = mock_llm_client
        self.mock_file_manager = mock_file_manager
        self.mock_content_generator = mock_content_generator
        
        # Reset mocks before each test
        self.mock_llm_client.reset_mock()
        self.mock_file_manager.reset_mock()
        self.mock_content_generator.reset_mock()
        
        # Set up common mock behaviors
        self.mock_file_manager.sanitize_path.side_effect = lambda x: x  # Pass through
        self.mock_file_manager.ensure_directory.return_value = True
        
        # Initialize test subject
        self.folder_generator = FolderGenerator(model="test-model", ollama_url="http://test-url:11434")
        
    def tearDown(self):
        """Clean up after tests"""
        # Remove temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_initialization(self):
        """Test FolderGenerator initialization"""
        self.assertEqual(self.folder_generator.llm_client, self.mock_llm_client)
        self.assertEqual(self.folder_generator.file_manager, self.mock_file_manager)
        self.assertEqual(self.folder_generator.content_generator, self.mock_content_generator)
        
    def test_generate_level1_folders(self):
        """Test _generate_level1_folders method"""
        # Mock LLM response
        level1_structure = {
            "folders": {
                "docs": {"description": "Documentation files"},
                "data": {"description": "Data files"}
            }
        }
        # Configure mock - return value instead of side_effect
        self.mock_llm_client.get_json_completion.return_value = level1_structure
        
        # Call the method
        result = self.folder_generator._generate_level1_folders("healthcare", "en", "doctor")
        
        # Check results
        self.assertEqual(result, level1_structure)
        
        # Verify the prompt used
        args, kwargs = self.mock_llm_client.get_json_completion.call_args
        self.assertIn("healthcare", kwargs["prompt"])
        self.assertIn("doctor", kwargs["prompt"])
        self.assertIn("en", kwargs["prompt"])
        
    def test_generate_level2_folders(self):
        """Test _generate_level2_folders method"""
        # Mock LLM response
        level2_structure = {
            "folders": {
                "clinical": {"description": "Clinical documents"},
                "admin": {"description": "Administrative documents"}
            }
        }
        # Configure mock - return value instead of side_effect
        self.mock_llm_client.get_json_completion.return_value = level2_structure
        
        # Call the method
        result = self.folder_generator._generate_level2_folders(
            "healthcare", "docs", "Documentation files", "en", "doctor"
        )
        
        # Check results
        self.assertEqual(result, level2_structure)
        
        # Verify the prompt used
        args, kwargs = self.mock_llm_client.get_json_completion.call_args
        self.assertIn("healthcare", kwargs["prompt"])
        self.assertIn("docs", kwargs["prompt"])
        self.assertIn("Documentation files", kwargs["prompt"])
        self.assertIn("en", kwargs["prompt"])
        self.assertIn("doctor", kwargs["prompt"])
        
    def test_generate_level3_folders(self):
        """Test _generate_level3_folders method"""
        # Mock LLM response
        level3_structure = {
            "folders": {
                "templates": {"description": "Document templates"},
                "examples": {"description": "Example documents"}
            }
        }
        # Configure mock - return value instead of side_effect
        self.mock_llm_client.get_json_completion.return_value = level3_structure
        
        # Call the method
        result = self.folder_generator._generate_level3_folders(
            "healthcare", "clinical", {"description": "Clinical documents"}, 
            "Documentation files", "docs", "en", "doctor"
        )
        
        # Check results
        self.assertEqual(result, level3_structure)
        
        # Verify the prompt used
        args, kwargs = self.mock_llm_client.get_json_completion.call_args
        self.assertIn("healthcare", kwargs["prompt"])
        self.assertIn("clinical", kwargs["prompt"])
        self.assertIn("Clinical documents", kwargs["prompt"])
        self.assertIn("docs", kwargs["prompt"])
        self.assertIn("en", kwargs["prompt"])
        self.assertIn("doctor", kwargs["prompt"])
        
    def test_generate_level3_files(self):
        """Test _generate_level3_files method"""
        # Mock LLM response
        level3_files = {
            "files": [
                {"name": "template1.docx", "description": "Template for clinical notes"},
                {"name": "example.pdf", "description": "Example clinical document"}
            ]
        }
        # Configure mock - return value instead of side_effect
        self.mock_llm_client.get_json_completion.return_value = level3_files
        
        # Call the method
        result = self.folder_generator._generate_level3_files(
            "healthcare", "clinical", {"description": "Clinical documents"}, 
            "Documentation files", "docs", "en", "doctor"
        )
        
        # Check results
        self.assertEqual(result, level3_files)
        
        # Verify the prompt used
        args, kwargs = self.mock_llm_client.get_json_completion.call_args
        self.assertIn("healthcare", kwargs["prompt"])
        self.assertIn("clinical", kwargs["prompt"])
        self.assertIn("Clinical documents", kwargs["prompt"])
        self.assertIn("docs", kwargs["prompt"])
        
    def test_generate_all(self):
        """Test generate_all method for creating complete folder structure"""
        # Create a simplified version of the test that mocks the actual process_folder_structure method
        # to avoid all the complex logic and make testing more direct
        with patch.object(self.folder_generator, '_generate_level1_folders') as mock_gen_l1, \
             patch.object(self.folder_generator, '_process_folder_structure') as mock_process:
            
            # Set up the mock return values
            level1_structure = {
                "folders": {
                    "docs": {"description": "Documentation files"}
                }
            }
            mock_gen_l1.return_value = level1_structure
            mock_process.return_value = True
            
            # Call the method
            result = self.folder_generator.generate_all(
                self.temp_dir, "healthcare", "doctor", "en"
            )
            
            # Verify results
            self.assertTrue(result)
            
            # Check that the proper methods were called with correct args
            mock_gen_l1.assert_called_once_with("healthcare", "en", "doctor")
            
            # Check that file_manager was called to create logs and target directories
            self.mock_file_manager.ensure_directory.assert_any_call(os.path.join(self.temp_dir, "logs"))
            self.mock_file_manager.ensure_directory.assert_any_call(os.path.join(self.temp_dir, "target"))
            
            # Verify process_folder_structure was called with correct args
            target_dir = os.path.join(self.temp_dir, "target")
            mock_process.assert_called_once_with(level1_structure, unittest.mock.ANY, "healthcare", "en", "doctor")
        
    def test_generate_files_only(self):
        """Test generate_files_only method for updating existing files"""
        # Mock directory structure using a simpler approach
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.is_dir') as mock_is_dir, \
             patch.object(self.folder_generator, '_regenerate_files') as mock_regen:
            
            # Set up mock behavior
            mock_exists.return_value = True
            mock_is_dir.return_value = True
            mock_regen.return_value = True
            
            # Call the method
            result = self.folder_generator.generate_files_only(
                self.temp_dir, "healthcare", "doctor", "en"
            )
            
            # Check results
            self.assertTrue(result)
            
            # Verify _regenerate_files was called with correct args
            mock_regen.assert_called_once()
            call_args = mock_regen.call_args[0]
            self.assertTrue("target" in str(call_args[0]))
            self.assertEqual("healthcare", call_args[1])
            self.assertEqual("en", call_args[2])
            self.assertEqual("doctor", call_args[3])


if __name__ == "__main__":
    unittest.main() 