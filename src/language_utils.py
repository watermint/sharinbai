#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import re
import locale
from typing import Dict, List, Any, Tuple
from datetime import date
from pathlib import Path
import traceback

# Internationalization libraries
import i18n
from babel.dates import format_date
from babel import Locale
from babel.core import UnknownLocaleError

# Setup logger
logger = logging.getLogger(__name__)

def get_resource_paths() -> List[Path]:
    """Get paths to resource directories
    
    Returns:
        List of Path objects to check for resource files
    """
    return [
        Path(__file__).parent.parent / "resources",
        Path("resources")
    ]

def init_i18n() -> None:
    """
    Initialize the i18n library with our language files
    """
    try:
        # Configure i18n
        resource_paths = get_resource_paths()
        
        # Set up i18n configuration
        i18n.set('fallback', 'en')
        i18n.set('filename_format', '{locale}.{format}')
        i18n.set('file_format', 'json')
        i18n.set('enable_memoization', True)
        
        # Add resource paths to i18n
        for resource_dir in resource_paths:
            if resource_dir.exists() and resource_dir.is_dir():
                i18n.load_path.append(str(resource_dir))
        
        logging.debug(f"Initialized i18n with paths: {i18n.load_path}")
    except Exception as e:
        logging.error(f"Error initializing i18n: {e}")

# Initialize i18n on module load
init_i18n()

def get_default_language() -> str:
    """Get the default language code for the application
    
    Returns:
        Default language code, typically 'en'
    """
    mapping_data = load_language_mapping()
    # Check for default in language_templates section first
    if "language_templates" in mapping_data and "default" in mapping_data["language_templates"]:
        return mapping_data["language_templates"]["default"]
    return "en"  # Fallback if not specified

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
                logger.error(f"Error loading language mapping file: {e}")
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

def is_supported_language_code(code: str) -> bool:
    """
    Check if a language code is directly supported in our language files
    (Used internally by get_normalized_language_key to avoid circular imports)
    
    Args:
        code: The language code to check
    
    Returns:
        True if supported, False otherwise
    """
    # Get supported languages
    mapping_data = load_language_mapping()
    
    # Check in language_templates
    if "language_templates" in mapping_data:
        templates = mapping_data["language_templates"]
        if code in templates and code != "default":
            return True
            
    # Check in available language files
    language_files = get_available_language_files()
    if code in language_files:
        return True
        
    return False

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
            for file_path in resource_path.glob("*.json"):
                # Skip non-language files
                if file_path.stem.lower() in ["language_mapping"]:
                    continue
                    
                # Extract language code from filename (e.g., "en.json" -> "en")
                lang_code = file_path.stem.lower()
                
                # Only add if we haven't seen this language code yet
                if lang_code not in language_files:
                    language_files[lang_code] = file_path
    
    logging.debug(f"Available language files: {list(language_files.keys())}")
    return language_files

def get_supported_languages() -> List[str]:
    """Get a list of supported language codes based on available resource files
    
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
    Check if a language is supported based on available resource files
    
    Args:
        language: Language code or name
    
    Returns:
        True if supported, False otherwise
    """
    if not language:
        return True  # Default language is always supported
        
    normalized = get_normalized_language_key(language, strict=False)
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

def get_normalized_language_key(language: str, strict: bool = False) -> str:
    """Standardize language code/name to a normalized format using i18n and Babel
    
    Args:
        language: The language string to normalize
        strict: If True, only accepts exact matches to supported languages
        
    Returns:
        Normalized language code
    """
    if not language:
        return get_default_language()
    
    # Replace underscores with hyphens which is i18n's standard separator
    lang_input = language.replace('_', '-')
    
    # Use i18n to check if this language is available first
    try:
        # i18n library uses lowercase locale keys internally
        clean_lang = lang_input.lower()
        
        # Check if this locale works with i18n directly
        if i18n.translations.has(clean_lang):
            return clean_lang
    except Exception as e:
        logging.debug(f"Error accessing i18n translations: {e}")
    
    # Use babel for standardized locale handling
    try:
        locale_obj = Locale.parse(lang_input)
        normalized = locale_obj.language
        
        # Add territory if present
        if locale_obj.territory:
            normalized = f"{normalized}-{locale_obj.territory}"
            
        # Check if we directly support this code
        if is_supported_language_code(normalized):
            return normalized
        
        # Extract language part for fallback
        base_lang = normalized.split('-')[0]
        if is_supported_language_code(base_lang):
            return base_lang
    except Exception as e:
        logging.debug(f"Error parsing locale with Babel: {e}")
    
    # Load language mappings from resource file
    mapping_data = load_language_mapping()
    
    # If language_templates is available, use that
    if "language_templates" in mapping_data:
        templates = mapping_data["language_templates"]
        
        # Convert to lowercase for case-insensitive matching
        lang_lower = lang_input.lower()
        
        # Direct match with a language code
        if lang_lower in templates and lang_lower != "default":
            return lang_lower
            
        # Look through each language's templates for matches
        for lang_code, aliases in templates.items():
            if lang_code == "default":
                continue
                
            if isinstance(aliases, list) and any(alias.lower() == lang_lower for alias in aliases):
                return lang_code
        
        # For strict mode, we don't want to do further processing
        if strict:
            return language
            
        # Try partial matching for language names
        for lang_code, aliases in templates.items():
            if lang_code == "default":
                continue
                
            if isinstance(aliases, list):
                for alias in aliases:
                    if alias.lower() in lang_lower or lang_lower in alias.lower():
                        return lang_code
    
    # Return the input as is if we couldn't normalize it
    # Let i18n handle the fallback behavior
    return language

def load_prompt_templates(language: str) -> Dict[str, Any]:
    """Load prompt templates for the specified language"""
    try:
        # Normalize language key
        normalized_lang = get_normalized_language_key(language, strict=False)
        
        # Get the base language code
        base_lang = normalized_lang.split('-')[0] if '-' in normalized_lang else normalized_lang
        
        # Get all available language files
        language_files = get_available_language_files()
        
        if not language_files:
            logging.critical("No language resource files found in resources directory")
            sys.exit(1)
            
        # Define priority for matching:
        # 1. Exact match for normalized language (en-gb.json for en-GB)
        # 2. Base language match (en.json for en-US)
        # 3. Any regional variant of the base language (en-us.json for en)
        
        template_file = None
        
        # 1. Try exact match first (case insensitive)
        if normalized_lang in language_files:
            template_file = language_files[normalized_lang]
            logging.info(f"Using exact match language file: {template_file}")
        
        # 2. If no exact match, try base language
        elif base_lang in language_files:
            template_file = language_files[base_lang]
            logging.info(f"Using base language file: {template_file}")
        
        # 3. If still no match, look for any variant
        else:
            for lang_code, file_path in language_files.items():
                file_base = lang_code.split('-')[0] if '-' in lang_code else lang_code
                if file_base == base_lang:
                    template_file = file_path
                    logging.info(f"Using regional variant file: {template_file}")
                    break
        
        # If still no match, use any available file as fallback (preferably English)
        if not template_file:
            # Try to find en.json as fallback
            if 'en' in language_files:
                template_file = language_files['en']
                logging.warning(f"No match found for {normalized_lang}, using English fallback: {template_file}")
            # Or any en-* variant
            else:
                for lang_code, file_path in language_files.items():
                    if lang_code.startswith('en-'):
                        template_file = file_path
                        logging.warning(f"No match found for {normalized_lang}, using English variant fallback: {template_file}")
                        break
            
            # If no English file, use the first available file
            if not template_file and language_files:
                first_key = next(iter(language_files))
                template_file = language_files[first_key]
                logging.warning(f"No match found for {normalized_lang}, using first available file: {template_file}")
        
        # Terminate with error if file not found
        if not template_file:
            logging.critical(f"No language file found for '{language}' (normalized to '{normalized_lang}')")
            logging.critical("Please ensure language files (e.g., en.json, ja.json) exist in the resources directory")
            sys.exit(1)
        
        # Load the selected file
        with open(template_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.critical(f"Cannot parse template file {template_file}: {e}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Error reading template file: {e}")
        logging.critical(f"Error details: {traceback.format_exc()}")
        sys.exit(1)

def get_date_format(date_obj: date, format_type: str = "prompt", language: str = "en-US") -> str:
    """
    Format a date according to the specified format and language.
    
    Args:
        date_obj: The date object to format
        format_type: The type of format to use ("prompt", "filename", "document")
        language: The language code
        
    Returns:
        The formatted date string
    """
    # Get normalized language key
    language_key = get_normalized_language_key(language)
    
    # Extract the locale code from the language key (e.g., 'en' from 'en-US')
    locale_code = language_key.split('-')[0] if '-' in language_key else language_key
    
    # Load language templates
    templates = load_prompt_templates(language_key)
    date_formats = templates.get("date_formats", {})
    
    # If it's a document format, use localized formatting
    if format_type == "document":
        try:
            # Use proper internationalization with Babel
            return format_date(date_obj, format='long', locale=locale_code)
        except Exception as e:
            logging.warning(f"Babel date formatting failed for locale {locale_code}: {e}")
            # Continue with fallback formatting
    
    # Check for language-specific date templates in the config
    date_template_dict = date_formats.get(format_type, {})
    if isinstance(date_template_dict, dict) and locale_code in date_template_dict:
        date_template = date_template_dict.get(locale_code)
        if date_template and "{" in date_template:
            # Handle template formats like "{year}年{month}月{day}日"
            month_name = date_obj.strftime("%B")
            return date_template.format(
                year=date_obj.year,
                month=date_obj.month,
                day=date_obj.day,
                month_name=month_name
            )
    
    # Get the format string for the requested format type
    # Use defaults if specific formats aren't defined
    if format_type == "prompt":
        date_format = date_formats.get("prompt_format", "%Y-%m-%d")
    elif format_type == "filename":
        date_format = date_formats.get("filename_format", "%Y%m%d")
    elif format_type == "document":
        date_format = date_formats.get("document_format", "%B %d, %Y")
    else:
        # Default format if format_type is unknown
        date_format = date_formats.get("default_format", "%Y-%m-%d")
    
    # For all other cases, use strftime with the format string
    try:
        return date_obj.strftime(date_format)
    except Exception as e:
        logging.warning(f"Error formatting date {date_obj} with format {date_format}: {e}")
        # Return a default format as fallback
        return date_obj.strftime("%Y-%m-%d")

def register_font(language: str) -> Tuple[str, Path]:
    """
    Register appropriate font for the language in reportlab
    
    Args:
        language: The language code
        
    Returns:
        Tuple containing (font_alias, font_path) or (None, None) if font not found
    """
    try:
        # Get the base language code
        base_lang = language.split('-')[0].lower() if '-' in language else language.lower()
        
        # Map language to actual font file found in resources
        font_map = {
            'en': 'NotoSans-VariableFont_wdth,wght',
            'ja': 'NotoSansJP-VariableFont_wght',
            'ko': 'NotoSansKR-VariableFont_wght',
            'zh': 'NotoSansSC-VariableFont_wght',  # Simplified Chinese
            'tw': 'NotoSansTC-VariableFont_wght',  # Traditional Chinese
        }
        
        # Get font name for this language
        font_name = font_map.get(base_lang, 'NotoSans-VariableFont_wdth,wght')
        font_alias = f"NotoSans{base_lang.upper()}"  # Create a simple alias name
        
        # Build font path - first try parent directory
        font_path = Path(__file__).parent.parent / "resources" / f"{font_name}.ttf"
        
        # If font doesn't exist in the parent directory, check current directory
        if not font_path.exists():
            font_path = Path("resources") / f"{font_name}.ttf"
        
        # If font still doesn't exist, return None
        if not font_path.exists():
            logging.error(f"Font file {font_name}.ttf not found for language {language}. No fallback will be used.")
            return None, None
        
        # Register font with reportlab
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont(font_alias, str(font_path)))
        logging.info(f"Registered font: {font_alias} for language {language}")
        return font_alias, font_path
    except Exception as e:
        logging.error(f"Error registering font for language {language}: {e}")
        logging.error(f"Error details: {traceback.format_exc()}")
        return None, None  # Return None, None on error

def compose_prompt(template: str, params: Dict[str, str], date_range: Tuple[date, date] = None, language: str = "en-US", system_prompt: str = None) -> str:
    """
    Compose a prompt by replacing placeholders in a template.
    
    Args:
        template: The template string
        params: Dictionary of parameters to replace in the template
        date_range: Optional date range to include
        language: Language code
        system_prompt: Optional system prompt
        
    Returns:
        The composed prompt
    """
    # Replace placeholders with parameters
    prompt = template
    for key, value in params.items():
        placeholder = f"{{{key}}}"
        if value is not None and placeholder in prompt:  # Only replace if value is not None
            prompt = prompt.replace(placeholder, value)
    
    # Add date range if available
    if date_range and "{date_range}" in prompt:
        start_date_str = get_date_format(date_range[0], "prompt", language)
        end_date_str = get_date_format(date_range[1], "prompt", language)
        
        # Load language templates
        templates = load_prompt_templates(language)
        date_range_format = templates.get("date_formats", {}).get("date_range_text", "Date Range: {start_date} - {end_date}")
        
        # Format the date range text using the template
        date_range_text = date_range_format.format(start_date=start_date_str, end_date=end_date_str)
        prompt = prompt.replace("{date_range}", date_range_text)
    
    # Prepend system prompt if provided
    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"
    
    return prompt 

def get_translation(key: str, locale: str = None, default: str = None, **kwargs) -> str:
    """
    Get a translated string using i18n
    
    Args:
        key: The translation key
        locale: The locale to use (defaults to default_language)
        default: The default value if translation not found
        **kwargs: Additional parameters for string formatting
        
    Returns:
        The translated string
    """
    if not locale:
        locale = get_default_language()
    
    # Normalize locale
    locale = get_normalized_language_key(locale)
    
    # Try i18n first
    try:
        # Only use the base language part for i18n lookups
        base_locale = locale.split('-')[0] if '-' in locale else locale
        
        # Check if the locale exists in i18n
        if i18n.translations.has(base_locale):
            result = i18n.t(key, locale=base_locale, **kwargs)
            if result != key:  # i18n returns the key if not found
                return result
    except Exception as e:
        logging.debug(f"Error getting translation with i18n: {e}")
    
    # Fallback to our custom approach
    try:
        templates = load_prompt_templates(locale)
        
        # Navigate through nested dict using the key parts
        parts = key.split('.')
        current = templates
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Key not found in templates
                return default if default is not None else key
        
        # If we found a string, return it
        if isinstance(current, str):
            # Apply string formatting if kwargs provided
            try:
                if kwargs:
                    return current.format(**kwargs)
                return current
            except KeyError:
                # Missing format parameters
                logging.warning(f"Missing format parameters for key {key} in locale {locale}")
                return current
        
        # If we found a dict or other non-string, return the default
        return default if default is not None else key
    
    except Exception as e:
        logging.error(f"Error getting translation for key {key} in locale {locale}: {e}")
        return default if default is not None else key 