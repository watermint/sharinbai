"""
Tests for the JSON Templates module
"""

import unittest
from src.structure.json_templates import JsonTemplates


class TestJsonTemplates(unittest.TestCase):
    """Test case for the JsonTemplates class"""
    
    def test_template_availability(self):
        """Test that all expected templates are available"""
        # Test that all expected template keys return non-empty strings
        template_keys = [
            'level1_folders',
            'level2_folders',
            'level3_folders',
            'level3_files',
            'complete_structure'
        ]
        
        for key in template_keys:
            template = JsonTemplates.get_template(key)
            self.assertTrue(template, f"Template for {key} should not be empty")
            self.assertIn('{{', template, f"Template for {key} should contain escaped opening braces")
            self.assertIn('}}', template, f"Template for {key} should contain escaped closing braces")
    
    def test_invalid_template_key(self):
        """Test behavior when an invalid template key is requested"""
        # Should return empty string for non-existent template
        template = JsonTemplates.get_template("non_existent_template")
        self.assertEqual("", template, "Should return empty string for non-existent template")
    
    def test_folder_templates_structure(self):
        """Test that folder templates have the expected structure"""
        # Test level1, level2, and level3 folder templates
        folder_template_keys = ['level1_folders', 'level2_folders', 'level3_folders']
        
        for key in folder_template_keys:
            template = JsonTemplates.get_template(key)
            self.assertIn('"folders"', template, f"Template for {key} should contain 'folders' key")
            self.assertIn('"description"', template, f"Template for {key} should contain 'description' key")
            self.assertIn('{folder_description}', template, f"Template for {key} should contain folder_description placeholder")
    
    def test_files_template_structure(self):
        """Test that files template has the expected structure"""
        template = JsonTemplates.get_template('level3_files')
        self.assertIn('"files"', template, "Files template should contain 'files' key")
        self.assertIn('"name"', template, "Files template should contain 'name' field")
        self.assertIn('"type"', template, "Files template should contain 'type' field")
        self.assertIn('"description"', template, "Files template should contain 'description' field")
        self.assertIn('{file_description}', template, "Files template should contain file_description placeholder")
    
    def test_complete_structure_template(self):
        """Test that the complete structure template has the expected elements"""
        template = JsonTemplates.get_template('complete_structure')
        self.assertIn('"folders"', template, "Complete structure template should contain 'folders' key")
        self.assertIn('"files"', template, "Complete structure template should contain 'files' key")
        self.assertIn('"name"', template, "Complete structure template should contain 'name' field")
        self.assertIn('"type"', template, "Complete structure template should contain 'type' field")
        self.assertIn('"description"', template, "Complete structure template should contain 'description' field")
        self.assertIn('{file_description}', template, "Complete structure template should contain file_description placeholder")


if __name__ == '__main__':
    unittest.main() 