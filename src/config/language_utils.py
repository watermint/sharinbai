"""
Language utilities for internationalization
"""

import os
import sys
import json
import logging
import re
import locale
from typing import Dict, List, Any, Optional
from pathlib import Path

def get_resource_paths() -> List[Path]:
    """
    Get paths to resource directories.
    
    Returns:
        List of Path objects to check for resource files
    """
    return [
        Path(__file__).parent.parent.parent / "resources",
        Path("resources")
    ]

def load_language_mapping() -> Dict:
    """
    Load language mapping data from the resource file.
    
    Returns:
        Dict: Language mapping data containing language_templates and other mappings
    """
    resource_paths = get_resource_paths()
    mapping_file = "language_mapping.json"
    
    for resource_dir in resource_paths:
        mapping_path = Path(resource_dir) / mapping_file
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading language mapping file: {e}")
                break
    
    # Fallback mapping if file not found
    return {
        "language_templates": {
            "en": ["english", "en", "us", "usa", "american", "en-us"],
            "en-GB": ["uk", "british", "england", "en-gb"],
            "ja": ["japanese", "ja", "japan", "jp", "ja-jp"],
            "default": "en"
        }
    }

def get_default_language() -> str:
    """
    Get the default language code for the application.
    
    Returns:
        Default language code, typically 'en'
    """
    mapping_data = load_language_mapping()
    # Check for default in language_templates section first
    if "language_templates" in mapping_data and "default" in mapping_data["language_templates"]:
        return mapping_data["language_templates"]["default"]
    return "en"  # Fallback if not specified

def get_available_language_files() -> Dict[str, Path]:
    """
    Scan resources directory for language files and return a mapping of 
    language codes to file paths.
    
    Returns:
        Dict mapping normalized language codes to their file paths
    """
    resource_paths = get_resource_paths()
    
    # Dictionary to store language code -> file path mapping
    language_files = {}
    
    # Scan all resource paths
    for resource_path in resource_paths:
        if resource_path.exists() and resource_path.is_dir():
            for file_path in resource_path.glob("prompts-*.json"):
                # Skip non-language files
                if file_path.stem.lower() in ["language_mapping"]:
                    continue
                    
                # Extract language code from filename (e.g., "prompts-en.json" -> "en")
                lang_code = file_path.stem.lower().replace("prompts-", "")
                
                # Only add if we haven't seen this language code yet
                if lang_code not in language_files:
                    language_files[lang_code] = file_path
    
    logging.debug(f"Available language files: {list(language_files.keys())}")
    return language_files

def get_supported_languages() -> List[str]:
    """
    Get a list of supported language codes based on available resource files.
    
    Returns:
        List of supported language codes
    """
    # Load language mappings from resource file
    mapping_data = load_language_mapping()
    
    # Return all language codes (keys) from language_templates except "default"
    if "language_templates" in mapping_data:
        return [lang for lang in mapping_data["language_templates"] 
                if lang != "default"]
    
    # Fallback: Get languages from available language files
    language_files = get_available_language_files()
    return list(language_files.keys())

def is_language_supported(language: str) -> bool:
    """
    Check if a language is supported based on available resource files.
    
    Args:
        language: Language code or name
    
    Returns:
        True if supported, False otherwise
    """
    if not language:
        return True  # Default language is always supported
        
    normalized = get_normalized_language_key(language)
    supported = get_supported_languages()
    
    # Direct match
    if normalized in supported:
        return True
        
    # Base language match (e.g., "en" for "en-US")
    base_lang = normalized.split('-')[0] if '-' in normalized else normalized
    if base_lang in supported:
        return True
        
    # Check if a language file exists for this language code
    language_files = get_available_language_files()
    if normalized in language_files or base_lang in language_files:
        return True
        
    return False

def get_normalized_language_key(language: str) -> str:
    """
    Standardize language code/name to a normalized format.
    
    Args:
        language: The language string to normalize
        
    Returns:
        Normalized language code
    """
    if not language:
        return ""
    
    # Replace underscores with hyphens which is standard separator
    lang_input = language.replace('_', '-')
    
    # Try simple normalization
    clean_lang = lang_input.lower()
    
    # Extract base language for fallback
    base_lang = clean_lang.split('-')[0] if '-' in clean_lang else clean_lang
    
    # Load language mappings from resource file
    mapping_data = load_language_mapping()
    
    # If language_templates is available, use that
    if "language_templates" in mapping_data:
        templates = mapping_data["language_templates"]
        
        # Direct match with a language code
        if clean_lang in templates and clean_lang != "default":
            return clean_lang
            
        # Look through each language's templates for matches
        for lang_code, aliases in templates.items():
            if lang_code == "default":
                continue
                
            if isinstance(aliases, list) and any(alias.lower() == clean_lang for alias in aliases):
                return lang_code
                
        # Try partial matching for language names
        for lang_code, aliases in templates.items():
            if lang_code == "default":
                continue
                
            if isinstance(aliases, list):
                for alias in aliases:
                    if alias.lower() in clean_lang or clean_lang in alias.lower():
                        return lang_code
    
    # Default to base language if all else fails
    return base_lang

def get_translation(key: str, language: str, default: str = None) -> str:
    """
    Get a translation for a key in a specific language.
    
    Args:
        key: Translation key
        language: Language code
        default: Default value if translation not found
    
    Returns:
        Translated string or default
    """
    language_files = get_available_language_files()
    normalized_lang = get_normalized_language_key(language)
    base_lang = normalized_lang.split('-')[0] if '-' in normalized_lang else normalized_lang
    
    # Define lookup order: exact match, base language, English
    lookup_order = [normalized_lang, base_lang, "en"]
    
    # Try each language in order
    for lang in lookup_order:
        if lang in language_files:
            try:
                with open(language_files[lang], 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    
                # Parse the dot notation key
                parts = key.split('.')
                current = translations
                
                # Navigate through the nested structure
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        current = None
                        break
                
                if current is not None and isinstance(current, str):
                    return current
            except Exception as e:
                logging.debug(f"Error loading translation for {lang}: {e}")
    
    # If no translation found, return default
    return default if default is not None else key 