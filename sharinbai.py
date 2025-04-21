#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Add project root to sys.path **BEFORE** other imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import logging
import argparse
from pathlib import Path
from src.config.settings import Settings
from src.config.logging_config import setup_logging
from src.config.ui_constants import ROLE_PROMPT_CLI
from src.config.language_utils import (
    get_default_language,
    get_normalized_language_key,
    get_supported_languages,
    is_language_supported,
    get_available_language_files,
    get_translation
)
from src.structure.folder_generator import FolderGenerator
from src.content.file_manager import FileManager

def extract_placeholders(text: str) -> set:
    """
    Extract placeholders in the format {placeholder} from a string,
    while excluding JSON patterns in example formats.
    
    Args:
        text: The string to extract placeholders from
        
    Returns:
        Set of placeholder names
    """
    import re
    if not isinstance(text, str):
        return set()
    
    # Known valid placeholders - these are the placeholders we should extract
    # This list is built based on actual placeholders used in the application
    valid_placeholders = {
        'industry', 'role', 'role_prompt', 'role_text', 'role_context',
        'l1_folder_name', 'l2_folder_name', 'l1_description', 'l2_description',
        'folder_structure', 'date_range', 'date_range_text', 'date_range_prompt',
        'date_organization_prompt', 'existing_structure_prompt', 'scenario_prompt',
        'start_date', 'end_date', 'date', 'start_year', 'end_year',
        'file_type', 'file_type_context', 'description', 'language',
        'scenario', 'structure', 'examples', 'doc_type', 'style_type', 'content_type',
        'failed_response', 'key', 'keys'
    }
    
    # Find all {placeholder} occurrences
    all_matches = re.findall(r'\{([^{}]+)\}', text)
    
    # Filter to only include valid placeholders, excluding JSON example patterns
    placeholders = set()
    for match in all_matches:
        # If it's in our valid_placeholders list, it's a real placeholder
        if match in valid_placeholders:
            placeholders.add(match)
        # If it looks like a single word without JSON syntax, it might be a placeholder we missed
        elif re.match(r'^[a-zA-Z_]+$', match) and '"' not in match and ':' not in match and ',' not in match:
            placeholders.add(match)
        # Otherwise it's probably a JSON example pattern, so we ignore it
    
    return placeholders

def get_value_at_key_path(obj, key_path):
    """
    Get the value at a specific key path in a nested dictionary.
    
    Args:
        obj: Dictionary to navigate
        key_path: Dot-separated key path
        
    Returns:
        Value at the key path or None if not found
    """
    parts = key_path.split(".")
    current = obj
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current

def test_languages():
    """
    Test all supported language resources and detect missing keys and placeholders.
    """
    file_manager = FileManager()
    language_files = get_available_language_files()
    
    if not language_files:
        print("No language resource files found.")
        return False
    
    print(f"Found {len(language_files)} language resource files.")
    
    # Load all language resources
    resources = {}
    
    # First pass: load all resources
    for lang_code, file_path in language_files.items():
        data = file_manager.read_json_file(str(file_path))
        if data:
            resources[lang_code] = data
    
    # No resources loaded
    if not resources:
        print("Failed to load any language resources.")
        return False
    
    # Get reference language (default to 'en' or first available)
    reference_lang = 'en' if 'en' in resources else next(iter(resources.keys()))
    print(f"Using {reference_lang} as reference language.")
    
    # Extract keys from reference language
    reference_keys = set()
    extract_keys(resources[reference_lang], "", reference_keys)
    
    # Build a mapping of placeholders for each key in the reference language
    reference_placeholders = {}
    for key in reference_keys:
        value = get_value_at_key_path(resources[reference_lang], key)
        if isinstance(value, str):
            placeholders = extract_placeholders(value)
            if placeholders:
                reference_placeholders[key] = placeholders
    
    # Second pass: check for missing keys and placeholders
    has_issues = False
    
    for lang_code, resource in resources.items():
        if lang_code == reference_lang:
            continue
            
        print(f"\nChecking {lang_code}:")
        missing_keys = []
        missing_placeholders = {}
        
        # Check for missing keys against reference language
        for key in reference_keys:
            if not key_exists(resource, key):
                missing_keys.append(key)
                has_issues = True
            elif key in reference_placeholders:
                # Check for missing placeholders in this key
                target_value = get_value_at_key_path(resource, key)
                if isinstance(target_value, str):
                    target_placeholders = extract_placeholders(target_value)
                    missing = reference_placeholders[key] - target_placeholders
                    if missing:
                        missing_placeholders[key] = missing
                        has_issues = True
        
        if missing_keys:
            print(f"  Missing {len(missing_keys)} key(s):")
            for key in sorted(missing_keys):
                print(f"    - {key}")
        else:
            print("  No missing keys found.")
            
        if missing_placeholders:
            print(f"  Missing placeholders in {len(missing_placeholders)} key(s):")
            for key, placeholders in sorted(missing_placeholders.items()):
                print(f"    - {key}: {', '.join(sorted(placeholders))}")
    
    return not has_issues

def extract_keys(obj, prefix, result_set):
    """
    Recursively extract all keys from a nested dictionary.
    
    Args:
        obj: Dictionary to extract keys from
        prefix: Current key prefix
        result_set: Set to store extracted keys
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                extract_keys(value, new_key, result_set)
            else:
                result_set.add(new_key)

def key_exists(obj, key_path):
    """
    Check if a key path exists in a nested dictionary.
    
    Args:
        obj: Dictionary to check
        key_path: Dot-separated key path
        
    Returns:
        True if key exists, False otherwise
    """
    parts = key_path.split(".")
    current = obj
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    def add_common_args(subparser):
        subparser.add_argument('--industry', '-i', type=str, help='Industry for the folder structure (if .metadata.json exists, this will temporarily override the stored value)')
        subparser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
        subparser.add_argument('--language', '-l', type=str, help='Language for the folder structure (can be omitted if .metadata.json exists)')
        subparser.add_argument('--model', '-m', type=str, default='llama3', help='Ollama model to use')
        subparser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry (if .metadata.json exists, this will temporarily override the stored value)')
        subparser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
        subparser.add_argument('--short', action='store_true', help='Enable short mode (max 5 items)')
    all_parser = subparsers.add_parser('all', help='Create folder structure and generate all files')
    add_common_args(all_parser)
    file_parser = subparsers.add_parser('file', help='Generate or update files in existing folder structure')
    add_common_args(file_parser)
    structure_parser = subparsers.add_parser('structure', help='Create only folder structure without generating files')
    add_common_args(structure_parser)
    subparsers.add_parser('list-languages', help='List supported languages')
    subparsers.add_parser('test-languages', help='Test all language resources for missing keys')
    parser.add_argument('--log-level', type=str, default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                       help='Logging level')
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    if args.command == 'list-languages':
        supported = get_supported_languages()
        if supported:
            print("Supported languages:")
            for lang in sorted(supported):
                print(f"  {lang}")
        else:
            print("No language resource files found.")
        sys.exit(0)
    elif args.command == 'test-languages':
        success = test_languages()
        sys.exit(0 if success else 1)
    
    # Initialize settings from args with default language
    settings = Settings().from_args(vars(args))
    
    # Set up logging early to capture any issues
    setup_logging(settings.log_level, settings.output_path)
    
    # Store original command line arguments for industry and role
    cli_industry = args.industry
    cli_role = args.role
    
    # If working with existing structure, try to retrieve metadata
    if args.command in ['file'] or (args.command in ['all', 'structure'] and Path(settings.output_path).exists()):
        target_dir = Path(settings.output_path) / "target"
        metadata_path = target_dir / ".metadata.json"
        
        if metadata_path.exists():
            file_manager = FileManager()
            metadata = file_manager.read_json_file(str(metadata_path))
            if metadata:
                # Store metadata values
                metadata_industry = metadata.get('industry')
                metadata_role = metadata.get('role')
                metadata_language = metadata.get('language')
                
                # Set base values from metadata
                if metadata_industry:
                    # Only use metadata industry if not explicitly provided via CLI
                    if not cli_industry:
                        settings.industry = metadata_industry
                        logging.info(f"Retrieved industry '{settings.industry}' from metadata")
                
                if metadata_role:
                    # Only use metadata role if not explicitly provided via CLI
                    if not cli_role:
                        settings.role = metadata_role
                        logging.info(f"Retrieved role '{settings.role}' from metadata")
                
                # Update language from metadata if not provided by args
                if not args.language and metadata_language:
                    settings.language = metadata_language
                    logging.info(f"Retrieved language '{settings.language}' from metadata")
    
    # Priority override: CLI arguments take precedence over metadata
    if cli_industry:
        if settings.industry != cli_industry:
            logging.info(f"Temporarily overriding industry from '{settings.industry}' to '{cli_industry}'")
        settings.industry = cli_industry
    
    if cli_role:
        if settings.role != cli_role:
            logging.info(f"Temporarily overriding role from '{settings.role}' to '{cli_role}'")
        settings.role = cli_role
    
    # Ask for industry/role/language if not provided and needed for new structure
    if args.command in ['all', 'structure']:
        # Ask for industry if not provided
        if not settings.industry:
            industry = input("Please enter the industry for the folder structure: ")
            if not industry.strip():
                logging.error("Industry is required but not provided")
                sys.exit(1)
            settings.industry = industry
        
        # Ask for role if not provided
        if not hasattr(settings, 'role') or settings.role is None:
            role = input(ROLE_PROMPT_CLI + " ")
            if not role.strip():
                logging.error("Role is required but not provided")
                sys.exit(1)
            settings.role = role
    
    # Ask for language if not provided for any command
    if not settings.language:
        supported = get_supported_languages()
        if supported:
            print("Supported languages:")
            for i, lang in enumerate(sorted(supported), 1):
                print(f"{i}. {lang}")
            
        language = input("Please select a language (enter language code or number from the list): ")
        if language.strip():
            # Convert numeric input to language code
            if language.isdigit() and int(language) > 0 and int(language) <= len(supported):
                selected_lang = sorted(supported)[int(language)-1]
                logging.info(f"Selected language [{selected_lang}] by number {language}")
                settings.language = selected_lang
            else:
                logging.info(f"Entered language: {language}")
                settings.language = language
        else:
            logging.error("Language is required but not provided")
            sys.exit(1)
    
    # Ensure we have industry for all commands
    if not settings.industry:
        logging.error("Industry is required but not provided. Use --industry/-i option or ensure .metadata.json exists.")
        sys.exit(1)
    
    # Normalize language
    settings.language = get_normalized_language_key(settings.language)
    if args.language and settings.language != args.language:
        logging.info(f"Normalized language from {args.language} to {settings.language}")
    
    # Echo back language selection
    logging.info(f"Using language: {settings.language}")
    
    # Show which resource files are being used
    language_files = get_available_language_files()
    if settings.language in language_files:
        logging.info(f"Using resource file: {language_files[settings.language]}")
    else:
        base_lang = settings.language.split('-')[0] if '-' in settings.language else settings.language
        if base_lang in language_files:
            logging.info(f"Using resource file for base language: {language_files[base_lang]}")
        else:
            fallback_lang = "en"
            if fallback_lang in language_files:
                logging.info(f"Language not found, using fallback resource file: {language_files[fallback_lang]}")
            else:
                logging.warning("No matching language resource file found.")
    
    if not is_language_supported(settings.language):
        logging.warning(f"Language '{settings.language}' is not directly supported. Using best available match.")
    
    folder_generator = FolderGenerator(settings.model, settings.ollama_url)
    try:
        success = False
        if args.command == 'all':
            logging.info(f"Generating complete folder structure for {settings.industry} industry")
            success = folder_generator.generate_all(
                settings.output_path, 
                settings.industry,
                settings.language,
                settings.role,
                args.short
            )
        elif args.command == 'file':
            logging.info(f"Generating files only for {settings.industry} industry")
            success = folder_generator.generate_files_only(
                settings.output_path,
                settings.industry,
                settings.language,
                settings.role,
                args.short
            )
        elif args.command == 'structure':
            logging.info(f"Creating folder structure only for {settings.industry} industry")
            success = folder_generator.generate_structure_only(
                settings.output_path,
                settings.industry,
                settings.language,
                settings.role,
                args.short
            )
        else:
            logging.error(f"Unknown command: {args.command}")
            sys.exit(1)
            
        if success:
            logging.info(f"Command '{args.command}' completed successfully")
            sys.exit(0)
        else:
            logging.error(f"Command '{args.command}' completed with errors")
            sys.exit(1)
    except Exception as e:
        logging.critical(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
