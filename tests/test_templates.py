#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
from pathlib import Path
import logging

# Add project root to sys.path **BEFORE** other imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.language_utils import get_available_language_files
from src.content.file_manager import FileManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def extract_placeholders(text):
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

def extract_keys_with_templates(obj, prefix, result_dict):
    """
    Recursively extract all string values with placeholders from a nested dictionary.
    
    Args:
        obj: Dictionary to extract values from
        prefix: Current key prefix
        result_dict: Dictionary to store extracted values with their keys
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                extract_keys_with_templates(value, new_key, result_dict)
            elif isinstance(value, str):
                placeholders = extract_placeholders(value)
                if placeholders:
                    result_dict[new_key] = {
                        "template": value,
                        "placeholders": placeholders
                    }

def generate_dummy_values(placeholders):
    """
    Generate dummy values for placeholders.
    
    Args:
        placeholders: Set of placeholder names
        
    Returns:
        Dictionary of placeholder names mapped to dummy values
    """
    dummy_values = {}
    for placeholder in placeholders:
        # Choose appropriate dummy value based on placeholder name
        if "date" in placeholder:
            dummy_values[placeholder] = "2023-05-15"
        elif "start_date" in placeholder:
            dummy_values[placeholder] = "2023-01-01"
        elif "end_date" in placeholder:
            dummy_values[placeholder] = "2023-12-31"
        elif "start_year" in placeholder:
            dummy_values[placeholder] = "2023"
        elif "end_year" in placeholder:
            dummy_values[placeholder] = "2024"
        elif "role" in placeholder:
            dummy_values[placeholder] = "Software Engineer"
        elif "industry" in placeholder:
            dummy_values[placeholder] = "Technology"
        elif "description" in placeholder:
            dummy_values[placeholder] = "Sample Document Description"
        elif "language" in placeholder:
            dummy_values[placeholder] = "English"
        elif "file" in placeholder or "type" in placeholder:
            dummy_values[placeholder] = "document.docx"
        elif "key" in placeholder or "keys" in placeholder:
            dummy_values[placeholder] = "example_key"
        elif "count" in placeholder:
            dummy_values[placeholder] = "5"
        elif "time" in placeholder:
            dummy_values[placeholder] = "10.5"
        elif "item" in placeholder:
            dummy_values[placeholder] = "sample_item"
        elif "structure" in placeholder:
            dummy_values[placeholder] = "Sample folder structure"
        elif "style" in placeholder or "style_type" in placeholder:
            dummy_values[placeholder] = "professional"
        elif "content" in placeholder or "content_type" in placeholder:
            dummy_values[placeholder] = "content"
        elif "scenario" in placeholder:
            dummy_values[placeholder] = "Business scenario example"
        elif "example" in placeholder or "examples" in placeholder:
            dummy_values[placeholder] = "Example text"
        elif "doc_type" in placeholder:
            dummy_values[placeholder] = "document"
        elif "l1_folder_name" in placeholder:
            dummy_values[placeholder] = "Level 1 Folder"
        elif "l2_folder_name" in placeholder:
            dummy_values[placeholder] = "Level 2 Folder"
        elif "l1_description" in placeholder:
            dummy_values[placeholder] = "Level 1 folder description"
        elif "l2_description" in placeholder:
            dummy_values[placeholder] = "Level 2 folder description"
        elif "folder_structure" in placeholder:
            dummy_values[placeholder] = "Folder A, Folder B, Folder C"
        elif "role_text" in placeholder:
            dummy_values[placeholder] = " for a Software Engineer"
        elif "industry_info" in placeholder:
            dummy_values[placeholder] = "This is technology industry information"
        elif "failed_response" in placeholder:
            dummy_values[placeholder] = "Invalid JSON response"
        elif "date_range_text" in placeholder:
            dummy_values[placeholder] = "2023-01-01 to 2023-12-31"
        else:
            # Default dummy value
            dummy_values[placeholder] = f"{placeholder}_value"
            
    return dummy_values

def test_placeholder_substitution(template, placeholders):
    """
    Test if all placeholders in a template can be individually substituted.
    
    Args:
        template: The template string
        placeholders: Set of placeholder names in the template
        
    Returns:
        Tuple of (success, error_message)
    """
    # Generate dummy values for all placeholders
    dummy_values = generate_dummy_values(placeholders)
    
    try:
        # Check if each placeholder can be formatted individually
        for placeholder in placeholders:
            # Create a simple template with just this placeholder
            test_template = "{" + placeholder + "}"
            test_template.format(**{placeholder: dummy_values[placeholder]})
        
        return True, None
    except Exception as e:
        return False, str(e)

def test_template_in_context(key, template, placeholders):
    """
    Test a template by attempting to use it in a context similar to how it would 
    be used in the actual application.
    
    Args:
        key: The key path of the template
        template: The template string
        placeholders: Set of placeholder names in the template
        
    Returns:
        Tuple of (success, error_message)
    """
    # Generate dummy values for all placeholders
    dummy_values = generate_dummy_values(placeholders)
    
    # Special handling for different template types based on their key path
    try:
        # Extract category from key path
        parts = key.split('.')
        category = parts[0] if parts else ""
        
        # Skip templates that are meant to be JSON payloads as they need special handling
        if (
            "json" in key.lower() or 
            "folder_structure_prompt" in key or 
            "{" in template and "}" in template and (
                '"folders"' in template or 
                '"files"' in template or 
                '"industry"' in template
            )
        ):
            # For JSON templates, just check if placeholders can be substituted
            return test_placeholder_substitution(template, placeholders)
        
        # For regular text templates, try to format with all placeholders
        formatted = template.format(**dummy_values)
        return True, None
    except Exception as e:
        return False, str(e)

def test_template(template, placeholders, key):
    """
    Test a template by formatting it with dummy values.
    
    Args:
        template: The template string
        placeholders: Set of placeholder names in the template
        key: The key path of the template
        
    Returns:
        Tuple of (success, result, error_message)
    """
    # First check if individual placeholders can be substituted
    individual_success, individual_error = test_placeholder_substitution(template, placeholders)
    if not individual_success:
        return False, None, f"Placeholder substitution failed: {individual_error}"
    
    # Then test in context if possible
    context_success, context_error = test_template_in_context(key, template, placeholders)
    if not context_success:
        return False, None, f"Context substitution failed: {context_error}"
    
    return True, "Template tested successfully", None

def write_summary_report(language_stats):
    """
    Write a summary report of all tested templates.
    
    Args:
        language_stats: Dictionary with statistics per language
        
    Returns:
        Path to the written summary report
    """
    summary = {
        "total_languages": len(language_stats),
        "total_templates": sum(stats["template_count"] for stats in language_stats.values()),
        "total_placeholders": sum(stats["total_placeholders"] for stats in language_stats.values()),
        "unique_placeholders": sorted(list(set().union(*[set(stats["unique_placeholders"]) for stats in language_stats.values()]))),
        "languages": language_stats
    }
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    report_path = os.path.join(output_dir, "template_testing_summary.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return report_path
    except Exception as e:
        logging.error(f"Failed to write summary report: {e}")
        return None

def test_templates():
    """
    Test all templates in language resource files.
    
    Returns:
        True if all tests pass, False otherwise
    """
    file_manager = FileManager()
    language_files = get_available_language_files()
    
    if not language_files:
        logging.error("No language resource files found.")
        return False
    
    logging.info(f"Found {len(language_files)} language resource files.")
    
    has_issues = False
    all_issues = []
    language_stats = {}
    
    # Process each language file
    for lang_code, file_path in language_files.items():
        logging.info(f"Testing templates in {lang_code}...")
        
        # Load the language resource file
        data = file_manager.read_json_file(str(file_path))
        if not data:
            logging.error(f"Failed to load language resource file for {lang_code}.")
            has_issues = True
            continue
        
        # Extract all templates with placeholders
        templates_with_placeholders = {}
        extract_keys_with_templates(data, "", templates_with_placeholders)
        
        template_count = len(templates_with_placeholders)
        logging.info(f"Found {template_count} templates with placeholders in {lang_code}.")
        
        # Collect statistics
        all_placeholders = []
        unique_placeholders = set()
        
        # Test each template
        file_issues = []
        for key, template_info in templates_with_placeholders.items():
            template = template_info["template"]
            placeholders = template_info["placeholders"]
            
            # Add to statistics
            all_placeholders.extend(placeholders)
            unique_placeholders.update(placeholders)
            
            success, result, error = test_template(template, placeholders, key)
            
            if not success:
                file_issues.append({
                    "key": key,
                    "template": template,
                    "placeholders": list(placeholders),
                    "error": error
                })
        
        # Store statistics for this language
        language_stats[lang_code] = {
            "template_count": template_count,
            "total_placeholders": len(all_placeholders),
            "unique_placeholders": sorted(list(unique_placeholders)),
            "placeholder_counts": {ph: all_placeholders.count(ph) for ph in unique_placeholders}
        }
        
        # Report issues for this file
        if file_issues:
            has_issues = True
            all_issues.extend([{**issue, "language": lang_code} for issue in file_issues])
            logging.error(f"Found {len(file_issues)} issues in {lang_code}:")
            for issue in file_issues:
                logging.error(f"  Key: {issue['key']}")
                logging.error(f"  Template: {issue['template']}")
                logging.error(f"  Placeholders: {', '.join(issue['placeholders'])}")
                logging.error(f"  Error: {issue['error']}")
                logging.error("")
        else:
            logging.info(f"No template issues found in {lang_code}.")
    
    # Write detailed report if issues found
    if all_issues:
        # Create output directory if it doesn't exist
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        report_path = os.path.join(output_dir, "template_issues_report.json")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(all_issues, f, ensure_ascii=False, indent=2)
            logging.info(f"Detailed issues report written to {report_path}")
        except Exception as e:
            logging.error(f"Failed to write detailed issues report: {e}")
    
    # Write summary report
    summary_path = write_summary_report(language_stats)
    if summary_path:
        logging.info(f"Summary report written to {summary_path}")
    
    return not has_issues

if __name__ == "__main__":
    logging.info("Starting template testing...")
    success = test_templates()
    if success:
        logging.info("All templates tested successfully!")
        sys.exit(0)
    else:
        logging.error("Template testing found issues. Check logs for details.")
        sys.exit(1) 