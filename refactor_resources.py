#!/usr/bin/env python3
"""
Script to remove the ui_strings section from all language resource files
"""

import os
import json
from pathlib import Path

def remove_ui_strings_from_resource(file_path):
    """
    Remove the ui_strings section from a language resource file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if ui_strings exists in the file
        if 'ui_strings' in data:
            # Remove ui_strings section
            del data['ui_strings']
            print(f"Removed ui_strings from {file_path}")
            
            # Write back the modified data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return True
        else:
            print(f"No ui_strings found in {file_path}")
            return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """
    Find all language resource files and remove ui_strings section
    """
    # Get the resources directory
    resources_dir = Path(__file__).parent / "resources"
    
    if not resources_dir.exists():
        print(f"Resources directory not found: {resources_dir}")
        return
    
    # Find all JSON files in the resources directory
    json_files = list(resources_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON resource files found")
        return
    
    print(f"Found {len(json_files)} resource files")
    
    # Remove ui_strings from each file
    modified_count = 0
    for file_path in json_files:
        # Skip language_mapping.json and any other non-language files
        if file_path.stem.lower() in ["language_mapping"]:
            continue
            
        if remove_ui_strings_from_resource(file_path):
            modified_count += 1
    
    print(f"Modified {modified_count} resource files")

if __name__ == "__main__":
    main() 