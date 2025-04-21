#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
from pathlib import Path
import shutil

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

def set_value_at_key_path(obj, key_path, value):
    """
    Set the value at a specific key path in a nested dictionary.
    
    Args:
        obj: Dictionary to navigate
        key_path: Dot-separated key path
        value: Value to set
        
    Returns:
        Updated dictionary
    """
    parts = key_path.split(".")
    current = obj
    
    # Navigate to the parent of the target
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Set the value at the target
    current[parts[-1]] = value
    return obj

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

def fix_language_resources():
    """
    Fix missing placeholders in all language resource files.
    """
    # Path to resources directory
    resources_dir = Path("resources")
    output_dir = Path("resources_fixed")
    
    # Make sure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    # Get all language resource files
    language_files = {}
    for file_path in resources_dir.glob("prompts-*.json"):
        # Extract language code from filename (e.g., "prompts-en.json" -> "en")
        lang_code = file_path.stem.lower().replace("prompts-", "")
        language_files[lang_code] = file_path
    
    if not language_files:
        print("No language resource files found.")
        return False
    
    print(f"Found {len(language_files)} language resource files to process.")
    
    # Load all language resources
    resources = {}
    for lang_code, file_path in language_files.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                resources[lang_code] = data
            except json.JSONDecodeError as e:
                print(f"Error loading {lang_code}: {e}")
    
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
    
    # Process and fix each language resource
    for lang_code, resource in resources.items():
        if lang_code == reference_lang:
            # Always copy the reference language file (it's already correct)
            shutil.copy2(language_files[lang_code], output_dir / language_files[lang_code].name)
            continue
        
        modified = False
        missing_keys = []
        fixed_placeholders = {}
        
        # Check for missing keys against reference language
        for key in reference_keys:
            if not key_exists(resource, key):
                missing_keys.append(key)
            elif key in reference_placeholders:
                # Check for missing placeholders in this key
                target_value = get_value_at_key_path(resource, key)
                if isinstance(target_value, str):
                    target_placeholders = extract_placeholders(target_value)
                    missing = reference_placeholders[key] - target_placeholders
                    if missing:
                        # We have missing placeholders to fix
                        fixed_placeholders[key] = missing
                        modified = True
                        
                        # Get the reference value with the placeholders
                        ref_value = get_value_at_key_path(resources[reference_lang], key)
                        
                        # Copy the missing placeholders from reference to this language
                        # We just keep the original text but ensure placeholders from reference language are added
                        new_value = target_value
                        for placeholder in missing:
                            # Only add if not already in the string (just to be safe)
                            if f"{{{placeholder}}}" not in new_value:
                                # Simple placeholder addition to preserve most of the translation
                                # This is a basic approach - more sophisticated methods would be needed
                                # for better placement of placeholders
                                new_value = new_value + f" {{{placeholder}}}"
                        
                        # Update the resource with fixed value
                        set_value_at_key_path(resource, key, new_value)
        
        # Save the fixed resource file
        output_path = output_dir / language_files[lang_code].name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resource, f, ensure_ascii=False, indent=4)
        
        if modified:
            print(f"Fixed {len(fixed_placeholders)} keys with missing placeholders in {lang_code}.")
            for key, placeholders in fixed_placeholders.items():
                print(f"  - {key}: {', '.join(sorted(placeholders))}")
        else:
            print(f"No fixes needed for {lang_code}.")
    
    print(f"\nFixed resource files have been saved to {output_dir}")
    return True

if __name__ == '__main__':
    fix_language_resources() 