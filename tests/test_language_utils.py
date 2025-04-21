"""
Tests for language utility functions
"""

import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from src.config.language_utils import (
    get_resource_paths,
    load_language_mapping,
    get_default_language,
    get_available_language_files,
    get_supported_languages,
    is_language_supported,
    get_normalized_language_key,
    get_translation
)


class TestLanguageUtils(unittest.TestCase):
    """Test cases for language utility functions"""
    
    def test_get_resource_paths(self):
        """Test get_resource_paths returns expected paths"""
        paths = get_resource_paths()
        self.assertTrue(isinstance(paths, list))
        self.assertTrue(all(isinstance(p, Path) for p in paths))
        self.assertTrue(len(paths) >= 2)
        
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"language_templates": {"en": ["english"], "default": "en"}}')
    def test_load_language_mapping(self, mock_file, mock_exists):
        """Test load_language_mapping loads the correct data"""
        # Mock that file exists
        mock_exists.return_value = True
        
        mapping = load_language_mapping()
        
        self.assertIn('language_templates', mapping)
        self.assertIn('en', mapping['language_templates'])
        self.assertEqual('en', mapping['language_templates']['default'])
        mock_file.assert_called_once()
        
    @patch('src.config.language_utils.load_language_mapping')
    def test_get_default_language(self, mock_load_mapping):
        """Test get_default_language returns the expected default"""
        # Set up mock return value
        mock_load_mapping.return_value = {
            "language_templates": {
                "en": ["english"],
                "fr": ["french"],
                "default": "fr"
            }
        }
        
        default_lang = get_default_language()
        self.assertEqual("fr", default_lang)
        mock_load_mapping.assert_called_once()
        
    @patch('src.config.language_utils.load_language_mapping')
    def test_get_default_language_fallback(self, mock_load_mapping):
        """Test get_default_language falls back to 'en' when no default is specified"""
        # Set up mock return value with no default
        mock_load_mapping.return_value = {
            "language_templates": {
                "en": ["english"],
                "fr": ["french"]
            }
        }
        
        default_lang = get_default_language()
        self.assertEqual("en", default_lang)
        mock_load_mapping.assert_called_once()
        
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.glob')
    def test_get_available_language_files(self, mock_glob, mock_is_dir, mock_exists):
        """Test get_available_language_files finds language files"""
        # Mock that paths exist and are directories
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        
        # Create mock Path objects for the glob results
        mock_en_path = MagicMock(spec=Path)
        mock_en_path.stem = "en"
        mock_en_path.name = "en.json"
        
        mock_fr_path = MagicMock(spec=Path)
        mock_fr_path.stem = "fr"
        mock_fr_path.name = "fr.json"
        
        mock_mapping_path = MagicMock(spec=Path)
        mock_mapping_path.stem = "language_mapping"
        mock_mapping_path.name = "language_mapping.json"
        
        # Set up glob to return our mock paths
        mock_glob.return_value = [mock_en_path, mock_fr_path, mock_mapping_path]
        
        language_files = get_available_language_files()
        
        self.assertIn("en", language_files)
        self.assertIn("fr", language_files)
        self.assertNotIn("language_mapping", language_files)
        
    @patch('src.config.language_utils.load_language_mapping')
    def test_get_supported_languages(self, mock_load_mapping):
        """Test get_supported_languages returns the correct supported languages"""
        # Set up mock return value
        mock_load_mapping.return_value = {
            "language_templates": {
                "en": ["english"],
                "fr": ["french"],
                "ja": ["japanese"],
                "default": "en"
            }
        }
        
        languages = get_supported_languages()
        self.assertIn("en", languages)
        self.assertIn("fr", languages)
        self.assertIn("ja", languages)
        self.assertNotIn("default", languages)
        mock_load_mapping.assert_called_once()
        
    @patch('src.config.language_utils.get_normalized_language_key')
    @patch('src.config.language_utils.get_supported_languages')
    @patch('src.config.language_utils.get_available_language_files')
    def test_is_language_supported(self, mock_get_files, mock_get_supported, mock_normalize):
        """Test is_language_supported correctly checks support"""
        # Set up mocks
        mock_normalize.return_value = "fr"
        mock_get_supported.return_value = ["en", "fr", "ja"]
        mock_get_files.return_value = {"en": None, "fr": None, "ja": None}
        
        # Direct match
        self.assertTrue(is_language_supported("French"))
        mock_normalize.assert_called_with("French")
        
        # Empty language defaults to True
        self.assertTrue(is_language_supported(""))
        
    @patch('src.config.language_utils.get_normalized_language_key')
    @patch('src.config.language_utils.get_supported_languages')
    @patch('src.config.language_utils.get_available_language_files')
    def test_is_language_supported_partial(self, mock_get_files, mock_get_supported, mock_normalize):
        """Test is_language_supported handles base language matches"""
        # Set up mocks
        mock_normalize.return_value = "en-US"
        mock_get_supported.return_value = ["en", "fr", "ja"]
        mock_get_files.return_value = {"en": None, "fr": None, "ja": None}
        
        # Base language match (en-US -> en)
        self.assertTrue(is_language_supported("en-US"))
        
    @patch('src.config.language_utils.load_language_mapping')
    def test_get_normalized_language_key(self, mock_load_mapping):
        """Test get_normalized_language_key normalizes language codes correctly"""
        # Set up mock mapping data
        mock_load_mapping.return_value = {
            "language_templates": {
                "en": ["english", "en", "us", "usa", "american", "en-us"],
                "en-GB": ["uk", "british", "england", "en-gb"],
                "ja": ["japanese", "ja", "japan", "jp", "ja-jp"],
                "default": "en"
            }
        }
        
        # Test cases
        test_cases = [
            ("english", "en"),
            ("ENGLISH", "en"),
            ("en", "en"),
            ("en-us", "en"),
            ("uk", "en-GB"),
            ("british", "en-GB"),
            ("japanese", "ja"),
            ("jp", "ja"),
            ("", "en"),  # Empty defaults to default language
            ("unknown", "unknown"),  # Unknown returns as-is (base form)
            ("fr-CA", "fr"),  # Extract base language
        ]
        
        for input_lang, expected_output in test_cases:
            self.assertEqual(
                get_normalized_language_key(input_lang),
                expected_output,
                f"Failed to normalize {input_lang} correctly"
            )
            
    @patch('builtins.open')
    @patch('src.config.language_utils.get_available_language_files')
    @patch('src.config.language_utils.get_normalized_language_key')
    def test_get_translation(self, mock_normalize, mock_get_files, mock_open_func):
        """Test get_translation returns the correct translation"""
        # Set up mocks
        mock_normalize.return_value = "fr"
        
        fr_path = Path("/resources/fr.json")
        en_path = Path("/resources/en.json")
        mock_get_files.return_value = {"fr": fr_path, "en": en_path}
        
        # French translation data
        fr_data = {"greeting": {"welcome": "Bienvenue"}}
        
        # Mock open to return different data based on file path
        mock_open_manager = mock_open()
        mock_open_func.side_effect = lambda path, mode, encoding: mock_open_manager.return_value
        
        # Set up the mock file contents
        mock_open_manager.return_value.read.return_value = json.dumps(fr_data)
        
        # Get translation
        translation = get_translation("greeting.welcome", "fr")
        
        self.assertEqual("Bienvenue", translation)
        mock_open_func.assert_called_with(fr_path, 'r', encoding='utf-8')
        
    @patch('builtins.open')
    @patch('src.config.language_utils.get_available_language_files')
    @patch('src.config.language_utils.get_normalized_language_key')
    def test_get_translation_fallback(self, mock_normalize, mock_get_files, mock_open_func):
        """Test get_translation falls back correctly"""
        # Set up mocks
        mock_normalize.return_value = "fr-CA"
        
        fr_path = Path("/resources/fr.json")
        en_path = Path("/resources/en.json")
        mock_get_files.return_value = {"fr": fr_path, "en": en_path}
        
        # French has no translation but English does
        fr_data = {"other_key": "Other value"}
        en_data = {"greeting": {"welcome": "Welcome"}}
        
        # Mock open to return different data based on file path
        def mock_read_data(path, mode, encoding):
            mock_file = mock_open().return_value
            if path == fr_path:
                mock_file.read.return_value = json.dumps(fr_data)
            elif path == en_path:
                mock_file.read.return_value = json.dumps(en_data)
            return mock_file
            
        mock_open_func.side_effect = mock_read_data
        
        # Get translation - should fall back to English
        translation = get_translation("greeting.welcome", "fr-CA")
        
        self.assertEqual("Welcome", translation)
        
    @patch('src.config.language_utils.get_available_language_files')
    @patch('src.config.language_utils.get_normalized_language_key')
    def test_get_translation_missing(self, mock_normalize, mock_get_files):
        """Test get_translation returns default for missing key"""
        # Set up mocks
        mock_normalize.return_value = "fr"
        mock_get_files.return_value = {}  # No language files
        
        # Get translation with default
        translation = get_translation("missing.key", "fr", "Default Text")
        
        self.assertEqual("Default Text", translation)
        
        # Get translation without default
        translation = get_translation("missing.key", "fr")
        
        self.assertEqual("missing.key", translation)


if __name__ == "__main__":
    unittest.main() 