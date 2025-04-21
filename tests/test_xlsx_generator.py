"""
Tests for the XlsxGenerator class
"""

import os
import unittest
from unittest.mock import patch, MagicMock, call

from src.content.generators.xlsx_generator import XlsxGenerator, XLSX_AVAILABLE


# Skip tests if openpyxl is not available
@unittest.skipIf(not XLSX_AVAILABLE, "openpyxl is not installed")
class TestXlsxGenerator(unittest.TestCase):
    """Test cases for XlsxGenerator"""
    
    def setUp(self):
        """Set up for tests"""
        # Create mocks
        self.mock_llm_client = MagicMock()
        
        # Mock BaseGenerator.get_file_path to avoid file system operations
        with patch('src.content.generators.base_generator.BaseGenerator.get_file_path') as mock_get_file_path:
            # Return a dummy path
            mock_get_file_path.return_value = "/test/path/test.xlsx"
            
            # Initialize test subject
            self.generator = XlsxGenerator(self.mock_llm_client)
    
    def test_validate_sheet_name(self):
        """Test the sheet name validation function"""
        test_cases = [
            # Normal case
            ("Sheet1", "Sheet1"),
            # Whitespace handling
            ("  Sheet2  ", "Sheet2"),
            # Invalid characters
            ("Sheet:with/invalid*chars?[here]", "Sheet_with_invalid_chars__here_"),
            # Too long (over 31 characters)
            ("ThisSheetNameIsMuchTooLongForExcelAndExceedsTheMaximumLengthLimit", "ThisSheetNameIsMuchTooLongForEx"),
            # Empty name
            ("", "Sheet"),
            # Only spaces
            ("   ", "Sheet"),
            # Only invalid characters
            ("[/:?*]", "______")
        ]
        
        for input_name, expected_output in test_cases:
            with self.subTest(input_name=input_name):
                result = self.generator._validate_sheet_name(input_name)
                self.assertEqual(result, expected_output)
    
    @patch('openpyxl.Workbook')
    @patch('src.content.generators.base_generator.BaseGenerator.create_prompt')
    @patch('src.config.language_utils.get_translation')
    def test_generate_with_sheet_name_validation(self, mock_get_translation, mock_create_prompt, mock_workbook_class):
        """Test generate method with sheet name validation"""
        # Mock workbook and related objects
        mock_workbook = mock_workbook_class.return_value
        mock_sheet = MagicMock()
        mock_workbook.active = mock_sheet
        mock_workbook.create_sheet.return_value = mock_sheet
        
        # Mock get_translation
        mock_get_translation.return_value = "test system message"
        
        # Mock create_prompt
        mock_create_prompt.return_value = "test prompt"
        
        # Mock LLM response with a sheet name that needs validation
        self.mock_llm_client.get_json_completion.return_value = {
            "sheets": [
                {
                    "name": "ThisSheetNameIsMuchTooLongForExcelAndExceedsTheMaximumLengthLimit",
                    "headers": ["Column1", "Column2"],
                    "data": [["data1", "data2"], ["data3", "data4"]]
                },
                {
                    "name": "Sheet:with/invalid*chars?[here]",
                    "headers": ["Column1", "Column2"],
                    "data": [["data1", "data2"], ["data3", "data4"]]
                }
            ]
        }
        
        # Call the method
        result = self.generator.generate("/test/dir", "test.xlsx", "test description", "test industry", "en")
        
        # Assert result
        self.assertTrue(result)
        
        # Assert workbook.create_sheet was called with the correct sanitized sheet names
        expected_calls = [
            call(title="ThisSheetNameIsMuchTooLongForEx"),
            call(title="Sheet_with_invalid_chars__here_")
        ]
        self.assertEqual(mock_workbook.create_sheet.call_args_list, expected_calls)

if __name__ == '__main__':
    unittest.main() 