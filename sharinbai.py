#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Add project root to sys.path **BEFORE** other imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import logging
import argparse
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from src.config.settings import Settings
from src.config.logging_config import setup_logging
from src.config.ui_constants import ROLE_PROMPT_CLI
from src.config.language_utils import (
    get_normalized_language_key,
    get_supported_languages,
    is_language_supported,
    get_available_language_files
)
from src.structure.folder_generator import FolderGenerator
from src.content.file_manager import FileManager
from tests.test_templates import test_templates as run_template_tests

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
    
    # Find all {placeholder} occurrences
    all_matches = re.findall(r'\{([^{}]+)\}', text)
    
    # Filter to only include likely placeholders, excluding JSON example patterns
    placeholders = set()
    for match in all_matches:
        # If it looks like a simple placeholder (single word, no JSON syntax)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', match) and '"' not in match and ':' not in match and ',' not in match:
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
    Test all supported language resources and detect missing keys, placeholders, 
    and test templates with placeholder compilation.
    """
    file_manager = FileManager()
    language_files = get_available_language_files()
    
    if not language_files:
        print("No language resource files found.")
        return False
    
    print(f"Found {len(language_files)} language resource files.")
    
    # PART 1: Testing for Missing Keys and Placeholders
    print("\n=== TESTING FOR MISSING KEYS AND PLACEHOLDERS ===\n")
    
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
    
    # Build a set of all valid placeholders from the reference language
    all_valid_placeholders = set()
    
    for key in reference_keys:
        value = get_value_at_key_path(resources[reference_lang], key)
        if isinstance(value, str):
            placeholders = extract_placeholders(value)
            if placeholders:
                reference_placeholders[key] = placeholders
                all_valid_placeholders.update(placeholders)
    
    print(f"Identified {len(all_valid_placeholders)} distinct placeholders in reference language.")
    
    # Second pass: check for missing keys and placeholders
    has_key_issues = False
    
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
                has_key_issues = True
            elif key in reference_placeholders:
                # Check for missing placeholders in this key
                target_value = get_value_at_key_path(resource, key)
                if isinstance(target_value, str):
                    # Extract placeholders from target text, but only consider those that are valid
                    # based on the reference language
                    raw_placeholders = extract_placeholders(target_value)
                    # Only include placeholders that are in the reference language's valid set
                    target_placeholders = {p for p in raw_placeholders if p in all_valid_placeholders}
                    
                    missing = reference_placeholders[key] - target_placeholders
                    if missing:
                        missing_placeholders[key] = missing
                        has_key_issues = True
        
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
        else:
            print("  No missing placeholders found.")
    
    # PART 2: Testing Templates with Placeholder Substitution
    print("\n=== TESTING TEMPLATES WITH PLACEHOLDER SUBSTITUTION ===\n")
    has_template_issues = not run_template_tests()
    
    # Return overall success status
    return not (has_key_issues or has_template_issues)

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

def test_templates():
    """
    Test all templates by filling placeholders with dummy values and checking for compilation errors.
    """
    return run_template_tests()

def process_batch_file(batch_file_path, log_level, log_path):
    """
    Process a batch YAML file containing multiple tasks.
    
    Args:
        batch_file_path: Path to the batch YAML file
        log_level: Logging level to use for all tasks
        log_path: Path where to store log files
        
    Returns:
        True if all tasks completed successfully, False otherwise
        
    Example batch YAML format:
    ```yaml
    model: "llama3"  # Common model for all tasks
    ollama_url: "http://localhost:11434"  # Common Ollama URL
    date_start: "2023-05-01"  # Common date range start
    date_end: "2023-05-31"  # Common date range end
    
    tasks:
      - mode: "all"  # Generate structure and files
        industry: "healthcare"
        path: "./out/healthcare"
        language: "en"
        role: "hospital administrator"
        # date_start and date_end override common settings
        date_start: "2023-06-01"
        date_end: "2023-06-30"
        
      - mode: "structure"  # Structure only
        industry: "finance"
        path: "./out/finance"
        language: "en"
        role: "financial analyst"
        # Uses common date range
    ```
    """
    try:
        with open(batch_file_path, 'r') as file:
            batch_data = yaml.safe_load(file)
    except Exception as e:
        logging.critical(f"Failed to load batch file: {e}")
        return False
        
    if not batch_data:
        logging.error("Batch file is empty or invalid")
        return False
        
    # Extract common settings if present
    common_model = batch_data.get('model', Settings.DEFAULT_MODEL)
    common_ollama_url = batch_data.get('ollama_url', None)
    
    # Calculate default date range values
    today = datetime.now()
    default_date_end = today.strftime("%Y-%m-%d")
    default_date_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Extract common date settings if present
    common_date_start = None
    common_date_end = None
    if 'date_start' in batch_data:
        try:
            common_date_start = datetime.strptime(batch_data['date_start'], "%Y-%m-%d")
        except ValueError:
            logging.warning(f"Invalid common date_start format: {batch_data['date_start']}. Expected YYYY-MM-DD.")
            common_date_start = datetime.strptime(default_date_start, "%Y-%m-%d")
    else:
        common_date_start = datetime.strptime(default_date_start, "%Y-%m-%d")
    
    if 'date_end' in batch_data:
        try:
            common_date_end = datetime.strptime(batch_data['date_end'], "%Y-%m-%d")
        except ValueError:
            logging.warning(f"Invalid common date_end format: {batch_data['date_end']}. Expected YYYY-MM-DD.")
            common_date_end = datetime.strptime(default_date_end, "%Y-%m-%d")
    else:
        common_date_end = datetime.strptime(default_date_end, "%Y-%m-%d")
    
    tasks = batch_data.get('tasks', [])
    if not tasks:
        logging.error("No tasks defined in batch file")
        return False
        
    logging.info(f"Processing {len(tasks)} tasks from batch file")
    
    # Track overall success
    all_successful = True
    
    for i, task in enumerate(tasks):
        logging.info(f"Processing task {i+1}/{len(tasks)}")
        
        # Extract task parameters with defaults
        mode = task.get('mode', 'all')
        if mode not in ['all', 'structure', 'file']:
            logging.error(f"Invalid mode '{mode}' in task {i+1}, skipping")
            all_successful = False
            continue
            
        # Parse task-specific date range if provided
        task_date_start = None
        if 'date_start' in task:
            try:
                task_date_start = datetime.strptime(task['date_start'], "%Y-%m-%d")
            except ValueError:
                logging.warning(f"Invalid task date_start format: {task['date_start']}. Expected YYYY-MM-DD.")
                task_date_start = common_date_start
        else:
            task_date_start = common_date_start
            
        task_date_end = None
        if 'date_end' in task:
            try:
                task_date_end = datetime.strptime(task['date_end'], "%Y-%m-%d")
            except ValueError:
                logging.warning(f"Invalid task date_end format: {task['date_end']}. Expected YYYY-MM-DD.")
                task_date_end = common_date_end
        else:
            task_date_end = common_date_end
            
        # Create args dictionary for this task
        task_args = {
            'command': mode,
            'industry': task.get('industry'),
            'path': task.get('path', './out'),
            'language': task.get('language'),
            'role': task.get('role'),
            'model': task.get('model', common_model),
            'ollama_url': task.get('ollama_url', common_ollama_url),
            'short': task.get('short', False),
            'log_level': log_level,
            'log_path': log_path,
            'date_start': task_date_start,
            'date_end': task_date_end
        }
        
        # Initialize settings from task args
        settings = Settings().from_args(task_args)
        
        # Process this task
        try:
            folder_generator = FolderGenerator(
                settings.model, 
                settings.ollama_url, 
                settings,
                date_start=task_date_start,
                date_end=task_date_end
            )
            
            success = False
            if mode == 'all':
                date_range_info = ""
                if task_date_start and task_date_end:
                    date_range_info = f", date range: {task_date_start.strftime('%Y-%m-%d')} to {task_date_end.strftime('%Y-%m-%d')}"
                
                logging.info(f"Starting task {i+1}: generating complete folder structure for {settings.industry} industry "
                             f"(language: {settings.language}, path: {settings.output_path}, "
                             f"model: {settings.model}, short: {task_args['short']}"
                             f"{', role: ' + settings.role if settings.role else ''}"
                             f"{date_range_info})")
                success = folder_generator.generate_all(
                    settings.output_path, 
                    settings.industry,
                    settings.language,
                    settings.role,
                    task_args['short'],
                    date_start=task_date_start,
                    date_end=task_date_end
                )
            elif mode == 'file':
                date_range_info = ""
                if task_date_start and task_date_end:
                    date_range_info = f", date range: {task_date_start.strftime('%Y-%m-%d')} to {task_date_end.strftime('%Y-%m-%d')}"
                
                logging.info(f"Starting task {i+1}: generating files only for {settings.industry} industry "
                             f"(language: {settings.language}, path: {settings.output_path}, "
                             f"model: {settings.model}, short: {task_args['short']}"
                             f"{', role: ' + settings.role if settings.role else ''}"
                             f"{date_range_info})")
                success = folder_generator.generate_files_only(
                    settings.output_path,
                    settings.industry,
                    settings.language,
                    settings.role,
                    task_args['short'],
                    date_start=task_date_start,
                    date_end=task_date_end
                )
            elif mode == 'structure':
                date_range_info = ""
                if task_date_start and task_date_end:
                    date_range_info = f", date range: {task_date_start.strftime('%Y-%m-%d')} to {task_date_end.strftime('%Y-%m-%d')}"
                
                logging.info(f"Starting task {i+1}: creating folder structure only for {settings.industry} industry "
                             f"(language: {settings.language}, path: {settings.output_path}, "
                             f"model: {settings.model}, short: {task_args['short']}"
                             f"{', role: ' + settings.role if settings.role else ''}"
                             f"{date_range_info})")
                success = folder_generator.generate_structure_only(
                    settings.output_path,
                    settings.industry,
                    settings.language,
                    settings.role,
                    task_args['short'],
                    date_start=task_date_start,
                    date_end=task_date_end
                )
                
            if success:
                logging.info(f"Task {i+1} completed successfully")
            else:
                logging.error(f"Task {i+1} completed with errors")
                all_successful = False
                
        except Exception as e:
            logging.error(f"Error in task {i+1}: {e}")
            all_successful = False
    
    return all_successful

def main():
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Calculate default date range values (30 days ago to today)
    today = datetime.now()
    default_date_end = today.strftime("%Y-%m-%d")
    default_date_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    
    def add_common_args(subparser):
        subparser.add_argument('--industry', '-i', type=str, help='Industry for the folder structure (if .metadata.json exists, this will temporarily override the stored value)')
        subparser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
        subparser.add_argument('--language', '-l', type=str, help='Language for the folder structure (can be omitted if .metadata.json exists)')
        subparser.add_argument('--model', '-m', type=str, default=Settings.DEFAULT_MODEL, help='Ollama model to use')
        subparser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry (if .metadata.json exists, this will temporarily override the stored value)')
        subparser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
        subparser.add_argument('--short', action='store_true', help='Enable short mode (max 5 items)')
        subparser.add_argument('--log-path', type=str, default='./logs', help='Path where to store log files')
        subparser.add_argument('--date-start', '-ds', type=str, default=default_date_start,
                              help=f'Start date for time-based content (format: YYYY-MM-DD). '
                                   f'This will be used to generate appropriate file names, folder names, '
                                   f'and content for time-based data. Defaults to {default_date_start}.')
        subparser.add_argument('--date-end', '-de', type=str, default=default_date_end,
                              help=f'End date for time-based content (format: YYYY-MM-DD). '
                                   f'Used with --date-start to define a date range for generating realistic '
                                   f'time-based content and file names. Defaults to {default_date_end}.')
    all_parser = subparsers.add_parser('all', help='Create folder structure and generate all files')
    add_common_args(all_parser)
    file_parser = subparsers.add_parser('file', help='Generate or update files in existing folder structure')
    add_common_args(file_parser)
    structure_parser = subparsers.add_parser('structure', help='Create only folder structure without generating files')
    add_common_args(structure_parser)
    
    # Add the batch command
    batch_parser = subparsers.add_parser('batch', help='Execute multiple tasks from a YAML file')
    batch_parser.add_argument('--file', '-f', type=str, required=True, help='Path to the batch YAML file')
    batch_parser.add_argument('--log-path', type=str, default='./logs', help='Path where to store log files')
    
    subparsers.add_parser('list-languages', help='List supported languages')
    test_languages_parser = subparsers.add_parser('test-languages', 
                                               help='Test all language resources for missing keys, placeholders, and template compilation')
    
    # Keep the test-templates command for backward compatibility
    subparsers.add_parser('test-templates', help='Test all templates with dummy placeholder values')
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
        print("Starting comprehensive language and template testing...")
        success = test_languages()
        if success:
            print("\nAll language and template tests passed successfully!")
        else:
            print("\nSome language or template tests failed. See details above.")
        sys.exit(0 if success else 1)
    elif args.command == 'test-templates':
        success = test_templates()
        sys.exit(0 if success else 1)
    elif args.command == 'batch':
        # Handle batch command
        setup_logging(args.log_level, "", args.log_path)
        logging.info(f"Processing batch file: {args.file}")
        success = process_batch_file(args.file, args.log_level, args.log_path)
        if success:
            logging.info("All batch tasks completed successfully")
            sys.exit(0)
        else:
            logging.error("Some batch tasks failed")
            sys.exit(1)
    
    # Initialize settings from args with default language
    settings = Settings().from_args(vars(args))
    
    # Parse date range parameters (they now always have values from defaults)
    date_start = None
    date_end = None
    
    if hasattr(args, 'date_start'):
        try:
            date_start = datetime.strptime(args.date_start, "%Y-%m-%d")
            logging.info(f"Using start date: {args.date_start}")
        except ValueError:
            logging.error(f"Invalid date_start format: {args.date_start}. Expected YYYY-MM-DD.")
            sys.exit(1)
            
    if hasattr(args, 'date_end'):
        try:
            date_end = datetime.strptime(args.date_end, "%Y-%m-%d")
            logging.info(f"Using end date: {args.date_end}")
        except ValueError:
            logging.error(f"Invalid date_end format: {args.date_end}. Expected YYYY-MM-DD.")
            sys.exit(1)
    
    # Set up logging early to capture any issues
    setup_logging(settings.log_level, settings.output_path, settings.log_path)
    
    # Store original command line arguments for industry and role
    cli_industry = args.industry
    cli_role = args.role
    
    # If working with existing structure, try to retrieve metadata
    if args.command in ['file'] or (args.command in ['all', 'structure'] and Path(settings.output_path).exists()):
        target_dir = Path(settings.output_path)
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
                
                # Update dates from metadata if not provided via CLI
                if not date_start and 'date_start' in metadata:
                    try:
                        date_start = datetime.strptime(metadata['date_start'], "%Y-%m-%d")
                        logging.info(f"Retrieved start date '{metadata['date_start']}' from metadata")
                    except ValueError:
                        logging.warning(f"Invalid date_start in metadata: {metadata['date_start']}")
                
                if not date_end and 'date_end' in metadata:
                    try:
                        date_end = datetime.strptime(metadata['date_end'], "%Y-%m-%d")
                        logging.info(f"Retrieved end date '{metadata['date_end']}' from metadata")
                    except ValueError:
                        logging.warning(f"Invalid date_end in metadata: {metadata['date_end']}")
    
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
    
    folder_generator = FolderGenerator(
        settings.model, 
        settings.ollama_url, 
        settings,
        date_start=date_start,
        date_end=date_end
    )
    try:
        success = False
        if args.command == 'all':
            date_range_info = ""
            if date_start and date_end:
                date_range_info = f", date range: {date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
            
            logging.info(f"Starting task: generating complete folder structure for {settings.industry} industry "
                         f"(language: {settings.language}, path: {settings.output_path}, "
                         f"model: {settings.model}, short: {args.short}"
                         f"{', role: ' + settings.role if settings.role else ''}"
                         f"{date_range_info})")
            success = folder_generator.generate_all(
                settings.output_path, 
                settings.industry,
                settings.language,
                settings.role,
                args.short,
                date_start=date_start,
                date_end=date_end
            )
        elif args.command == 'file':
            date_range_info = ""
            if date_start and date_end:
                date_range_info = f", date range: {date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
            
            logging.info(f"Starting task: generating files only for {settings.industry} industry "
                         f"(language: {settings.language}, path: {settings.output_path}, "
                         f"model: {settings.model}, short: {args.short}"
                         f"{', role: ' + settings.role if settings.role else ''}"
                         f"{date_range_info})")
            success = folder_generator.generate_files_only(
                settings.output_path,
                settings.industry,
                settings.language,
                settings.role,
                args.short,
                date_start=date_start,
                date_end=date_end
            )
        elif args.command == 'structure':
            date_range_info = ""
            if date_start and date_end:
                date_range_info = f", date range: {date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
            
            logging.info(f"Starting task: creating folder structure only for {settings.industry} industry "
                         f"(language: {settings.language}, path: {settings.output_path}, "
                         f"model: {settings.model}, short: {args.short}"
                         f"{', role: ' + settings.role if settings.role else ''}"
                         f"{date_range_info})")
            success = folder_generator.generate_structure_only(
                settings.output_path,
                settings.industry,
                settings.language,
                settings.role,
                args.short,
                date_start=date_start,
                date_end=date_end
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
