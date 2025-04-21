#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import re
from pathlib import Path

# Add project root to sys.path **BEFORE** other imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

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

def test_fixed_resources():
    """
    Test all fixed language resources and detect if any placeholders are still missing.
    """
    file_manager = FileManager()
    
    # Get all fixed language files
    resources_dir = Path("resources_fixed")
    if not resources_dir.exists():
        print("Fixed resources directory not found.")
        return False
    
    # Get all language resource files
    language_files = {}
    for file_path in resources_dir.glob("prompts-*.json"):
        # Extract language code from filename (e.g., "prompts-en.json" -> "en")
        lang_code = file_path.stem.lower().replace("prompts-", "")
        language_files[lang_code] = file_path
    
    if not language_files:
        print("No fixed language resource files found.")
        return False
    
    print(f"Found {len(language_files)} fixed language resource files.")
    
    # Load all language resources
    resources = {}
    
    # First pass: load all resources
    for lang_code, file_path in language_files.items():
        data = file_manager.read_json_file(str(file_path))
        if data:
            resources[lang_code] = data
    
    # No resources loaded
    if not resources:
        print("Failed to load any fixed language resources.")
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
        else:
            print("  No missing placeholders found.")
    
    if not has_issues:
        print("\nSuccess! All language resources are complete with no missing placeholders.")
        
    return not has_issues

if __name__ == '__main__':
    test_fixed_resources() 