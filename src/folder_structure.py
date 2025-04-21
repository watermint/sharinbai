#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set

# Import from local modules
from src.language_utils import get_normalized_language_key, load_prompt_templates, get_date_format, compose_prompt
from src.llm_utils import call_ollama_json

# Default model
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

def format_structure(structure: Dict[str, Any], indent: int = 0) -> str:
    """
    Format a structure dictionary as a string for display
    
    Args:
        structure: The structure dictionary to format
        indent: Current indentation level for recursive calls
        
    Returns:
        Formatted string representation of the structure
    """
    result = []
    
    # Process folders
    if "folders" in structure and isinstance(structure["folders"], dict):
        for folder_name, folder_data in structure["folders"].items():
            # Add folder with description if available
            if isinstance(folder_data, dict) and "description" in folder_data:
                description = folder_data["description"]
                result.append(" " * indent + f"- {folder_name}: {description}")
                
                # Process subfolders recursively with increased indentation
                substructure = format_structure(folder_data, indent + 2)
                if substructure:
                    result.append(substructure)
            else:
                # Simple folder without description
                result.append(" " * indent + f"- {folder_name}")
    
    # Process files
    if "files" in structure and isinstance(structure["files"], list):
        for file_info in structure["files"]:
            if isinstance(file_info, dict) and "name" in file_info:
                file_name = file_info["name"]
                file_desc = file_info.get("description", "")
                
                if file_desc:
                    result.append(" " * indent + f"  * {file_name}: {file_desc}")
                else:
                    result.append(" " * indent + f"  * {file_name}")
    
    return "\n".join(result)

def get_hierarchical_folder_structure(industry, language, role=None, date_range=None, model=DEFAULT_OLLAMA_MODEL, json_retry=5, ollama_url=None):
    """Get a hierarchical folder structure for the industry and create directories sequentially"""
    logging.info(f"Generating hierarchical folder structure for {industry} industry")
    
    # Import here to avoid circular imports
    from src.file_utils import create_directory_structure
    
    # We'll create the directory structure in the main function, no need to create it here
    # The passed current_dir parameter will determine where the structure is created
    
    # Get the top-level folder structure first
    level1_structure = generate_level1_folders(
        industry=industry,
        language=language,
        role=role,
        model=model
    )
    
    # Validate the structure before proceeding
    if not level1_structure or not isinstance(level1_structure, dict):
        logging.error(f"Invalid level 1 structure received: {level1_structure}")
        return None
        
    if "folders" not in level1_structure or not isinstance(level1_structure["folders"], dict):
        logging.error("Missing or invalid 'folders' key in level 1 structure")
        return None
    
    # Log the structure for debugging
    logging.info(f"Level 1 folders: {list(level1_structure['folders'].keys())}")
    
    # Process level 2 and level 3 folders for each level 1 folder
    for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
        if isinstance(l1_folder_data, dict) and "description" in l1_folder_data:
            logging.info(f"Processing level 2 and 3 folders for {l1_folder_name}")
            # Process level 2 folders (which in turn processes level 3 folders)
            updated_l1_data = process_level2_folders(
                industry=industry,
                level1_structure=level1_structure,
                l1_folder_name=l1_folder_name,
                l1_folder_data=l1_folder_data,
                language=language,
                role=role,
                date_range=date_range,
                model=model,
                json_retry=json_retry,
                ollama_url=ollama_url
            )
            # Update the level 1 structure with the processed data
            level1_structure["folders"][l1_folder_name] = updated_l1_data
            
            # Count and log the number of level 2 folders
            if "folders" in updated_l1_data and isinstance(updated_l1_data["folders"], dict):
                level2_folders = list(updated_l1_data["folders"].keys())
                logging.info(f"Created {len(level2_folders)} level 2 folders in '{l1_folder_name}': {level2_folders}")
                
                # Count level 3 folders
                level3_folder_count = 0
                for l2_folder_name, l2_folder_data in updated_l1_data["folders"].items():
                    if isinstance(l2_folder_data, dict) and "folders" in l2_folder_data and isinstance(l2_folder_data["folders"], dict):
                        level3_folder_count += len(l2_folder_data["folders"])
                        if l2_folder_data["folders"]:
                            logging.info(f"Level 3 folders in '{l2_folder_name}': {list(l2_folder_data['folders'].keys())}")
                
                logging.info(f"Total level 3 folders created: {level3_folder_count}")
        else:
            logging.warning(f"Skipping level 1 folder without description: {l1_folder_name}")
    
    logging.info("Hierarchical folder structure generation complete")
    # Return the complete hierarchical structure
    return level1_structure

def process_level2_folders(
    industry: str,
    level1_structure: dict,
    l1_folder_name: str,
    l1_folder_data: dict,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[str] = None,
    model: str = DEFAULT_OLLAMA_MODEL,
    json_retry: int = 5,
    ollama_url: Optional[str] = None
) -> dict:
    """Process level 2 folders for a given level 1 folder"""
    # Import here to avoid circular imports
    from src.file_utils import create_directory_structure
    
    # Check if we already have folders in this structure
    if "folders" in l1_folder_data and l1_folder_data["folders"]:
        logging.info(f"Level 2 folders already exist for {l1_folder_name}")
        
        # Process level 3 folders for each level 2 folder
        for l2_folder_name, l2_folder_data in l1_folder_data["folders"].items():
            # Only process dictionaries with a description
            if isinstance(l2_folder_data, dict) and "description" in l2_folder_data:
                # Process level 3 folders for this level 2 folder
                l3_structure = process_level3_folders(
                    industry=industry,
                    l2_folder_name=l2_folder_name,
                    l2_folder_data=l2_folder_data,
                    l1_description=l1_folder_data.get("description", ""),
                    l1_folder_name=l1_folder_name,
                    language=language,
                    role=role,
                    date_range=date_range,
                    model=model,
                    json_retry=json_retry,
                    ollama_url=ollama_url
                )
                
                # Update the level 2 structure with level 3 data
                l2_folder_data["folders"] = l3_structure.get("folders", {})
                if "files" in l3_structure:
                    l2_folder_data["files"] = l3_structure["files"]
            else:
                logging.warning(f"Skipping level 2 folder without description: {l2_folder_name}")
                # Ensure there's at least a valid structure
                if not isinstance(l2_folder_data, dict):
                    l1_folder_data["folders"][l2_folder_name] = {"description": l2_folder_name, "folders": {}, "files": []}
        
        return l1_folder_data
        
    logging.info(f"Generating level 2 folders for {l1_folder_name}")
    
    # Create prompt for level 2 folder structure
    l1_description = l1_folder_data.get("description", "")
    prompt = get_level2_folder_structure_prompt(
        industry=industry,
        l1_folder_name=l1_folder_name,
        l1_description=l1_description,
        language=language,
        role=role,
        date_range=date_range
    )
    
    # Generate folder structure using LLM
    try:
        response = call_ollama_json(
            prompt=prompt,
            model=model,
            ollama_url=ollama_url,
            structure_hint=f"The JSON should have a structure with keys like 'folders'",
            max_attempts=json_retry,
            language=language
        )
        
        # Validate response
        if not response or not isinstance(response, dict):
            logging.error(f"Invalid level 2 response for {l1_folder_name}: {response}")
            l1_folder_data["folders"] = {}
            return l1_folder_data
            
        # Validate folders key
        if "folders" not in response or not isinstance(response["folders"], dict):
            logging.error(f"Missing or invalid 'folders' key in level 2 response for {l1_folder_name}")
            l1_folder_data["folders"] = {}
            return l1_folder_data
            
        # Log the structure for debugging
        logging.info(f"Level 2 folders for {l1_folder_name}: {list(response['folders'].keys())}")
        
        # Merge the response into the level 1 folder data
        if response and "folders" in response:
            l1_folder_data["folders"] = response["folders"]
            logging.info(f"Successfully generated level 2 folders for {l1_folder_name}")
            
            # Process level 3 folders for each level 2 folder
            for l2_folder_name, l2_folder_data in l1_folder_data["folders"].items():
                # Only process dictionaries with a description
                if isinstance(l2_folder_data, dict) and "description" in l2_folder_data:
                    # Process level 3 folders for this level 2 folder
                    l3_structure = process_level3_folders(
                        industry=industry,
                        l2_folder_name=l2_folder_name,
                        l2_folder_data=l2_folder_data,
                        l1_description=l1_description,
                        l1_folder_name=l1_folder_name,
                        language=language,
                        role=role,
                        date_range=date_range,
                        model=model,
                        json_retry=json_retry,
                        ollama_url=ollama_url
                    )
                    
                    # Update the level 2 structure with level 3 data
                    l2_folder_data["folders"] = l3_structure.get("folders", {})
                    if "files" in l3_structure:
                        l2_folder_data["files"] = l3_structure["files"]
                else:
                    logging.warning(f"Skipping level 2 folder without description: {l2_folder_name}")
                    # Ensure there's at least a valid structure
                    if not isinstance(l2_folder_data, dict):
                        l1_folder_data["folders"][l2_folder_name] = {"description": l2_folder_name, "folders": {}, "files": []}
    except Exception as e:
        logging.error(f"Error generating level 2 folders for {l1_folder_name}: {e}")
        # Create an empty folders structure as fallback
        l1_folder_data["folders"] = {}
    
    return l1_folder_data

def process_level3_folders(
    industry: str,
    l2_folder_name: str,
    l2_folder_data: dict,
    l1_description: str,
    l1_folder_name: str,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None,
    model: str = DEFAULT_OLLAMA_MODEL,
    json_retry: int = 5,
    ollama_url: Optional[str] = None
) -> dict:
    """Process level 3 folders for a given level 2 folder"""
    # Check if we already have folders in this structure
    if "folders" in l2_folder_data and l2_folder_data["folders"]:
        logging.info(f"Level 3 folders already exist for {l2_folder_name}")
        return l2_folder_data
        
    logging.info(f"Generating level 3 folders for {l2_folder_name}")
    
    # Create prompt for level 3 folder structure
    prompt = get_level3_folder_structure_prompt(
        industry=industry,
        l2_folder_name=l2_folder_name,
        l2_folder_data=l2_folder_data,
        l1_description=l1_description,
        l1_folder_name=l1_folder_name,
        language=language,
        role=role,
        date_range=date_range
    )
    
    # Generate folder structure using LLM
    try:
        response = call_ollama_json(
            prompt=prompt,
            model=model,
            ollama_url=ollama_url,
            structure_hint=f"The JSON should have a structure with keys like 'folders'",
            max_attempts=json_retry,
            language=language
        )
        
        # Validate response
        if not response or not isinstance(response, dict):
            logging.error(f"Invalid level 3 response for {l2_folder_name}: {response}")
            l2_folder_data["folders"] = {}
            l2_folder_data["files"] = []
            return l2_folder_data
            
        # Validate folders key
        if "folders" not in response or not isinstance(response["folders"], dict):
            logging.warning(f"Missing or invalid 'folders' key in level 3 response for {l2_folder_name}")
            response["folders"] = {}
            
        # Log the structure for debugging
        if response["folders"]:
            logging.info(f"Level 3 folders for {l2_folder_name}: {list(response['folders'].keys())}")
        else:
            logging.info(f"No level 3 folders for {l2_folder_name}")
        
        # Generate file structure
        level3_files = process_level3_files(
            industry=industry,
            l2_folder_name=l2_folder_name,
            l2_folder_data=l2_folder_data,
            l1_description=l1_description,
            l1_folder_name=l1_folder_name,
            language=language,
            role=role,
            date_range=date_range,
            model=model,
            json_retry=json_retry,
            ollama_url=ollama_url
        )
        
        # Merge files into the response
        if level3_files and "files" in level3_files and level3_files["files"]:
            response["files"] = level3_files["files"]
            logging.info(f"Added {len(level3_files['files'])} files to {l2_folder_name}")
        
        # Merge the response into the level 2 folder data
        l2_folder_data["folders"] = response.get("folders", {})
        if "files" in response:
            l2_folder_data["files"] = response["files"]
        
        logging.info(f"Successfully generated level 3 structure for {l2_folder_name}")
        return l2_folder_data
    except Exception as e:
        logging.error(f"Error in process_level3_folders: {e}")
        l2_folder_data["folders"] = {}
        l2_folder_data["files"] = []
        return l2_folder_data

def process_level3_files(
    industry: str,
    l2_folder_name: str,
    l2_folder_data: dict,
    l1_description: str,
    l1_folder_name: str,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None,
    model: str = DEFAULT_OLLAMA_MODEL,
    json_retry: int = 5,
    ollama_url: Optional[str] = None
) -> dict:
    """Process level 3 files for a given level 2 folder"""
    # Check if we already have files in this structure
    if "files" in l2_folder_data and l2_folder_data["files"]:
        logging.info(f"Files already exist for {l2_folder_name}")
        return l2_folder_data
    
    logging.info(f"Generating files for {l2_folder_name}")
    
    # Create prompt for level 3 file structure
    prompt = get_level3_files_prompt(
        industry=industry,
        l2_folder_name=l2_folder_name,
        l2_folder_data=l2_folder_data,
        l1_description=l1_description,
        l1_folder_name=l1_folder_name,
        language=language,
        role=role,
        date_range=date_range
    )
    
    # Generate file structure using LLM
    try:
        response = call_ollama_json(
            prompt=prompt,
            model=model,
            ollama_url=ollama_url,
            structure_hint=f"The JSON should have a structure with keys like 'files'",
            max_attempts=json_retry,
            language=language
        )
        
        # Validate response
        if not response or not isinstance(response, dict):
            logging.error(f"Invalid file response for {l2_folder_name}: {response}")
            return {"files": []}
        
        # Validate files key
        if "files" not in response or not isinstance(response["files"], list):
            logging.warning(f"Missing or invalid 'files' key in response for {l2_folder_name}")
            return {"files": []}
        
        # Log the structure for debugging
        logging.info(f"Generated {len(response['files'])} files for {l2_folder_name}")
        
        return response
    except Exception as e:
        logging.error(f"Error in process_level3_files: {e}")
        return {"files": []}

def get_level2_folder_structure_prompt(
    industry: str,
    l1_folder_name: str,
    l1_description: str,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None
) -> str:
    """Create prompt for level 2 folder structure generation"""
    # Load templates for the specified language
    templates = load_prompt_templates(language)
    
    # Check both singular and plural forms for backward compatibility
    prompt_templates = templates.get("folder_structure_prompts", templates.get("folder_structure_prompt", {}))
    
    # Get system prompt template
    system_prompt = prompt_templates.get("level2_system_prompt", prompt_templates.get("system_prompt", prompt_templates.get("system")))
    if not system_prompt:
        logging.critical("Level 2 system prompt template not found in language configuration")
        sys.exit(1)
    
    # Get level 2 user prompt template
    level2_prompt_template = prompt_templates.get("level2_user_prompt", prompt_templates.get("level2"))
    if not level2_prompt_template:
        logging.critical("Level 2 user prompt template not found in language configuration")
        sys.exit(1)
    
    # Get role format template for the language
    role_formatted = ""
    if role:
        role_templates = templates.get("role_templates", {}).get(language, {})
        role_format = role_templates.get("role_format", " for {role}")
        role_formatted = role_format.format(role=role)
    
    # Create parameters for the template
    params = {
        "industry": industry,
        "l1_folder_name": l1_folder_name,
        "l1_description": l1_description,
        "role": role if role else "",
        "role_text": role_formatted
    }
    
    # Compose the prompt - the template already includes the instruction to return only JSON
    prompt = compose_prompt(level2_prompt_template, params, date_range, language, system_prompt)
    
    return prompt

def get_level3_folder_structure_prompt(
    industry: str,
    l2_folder_name: str,
    l2_folder_data: dict,
    l1_description: str,
    l1_folder_name: str,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None
) -> str:
    """Create prompt for level 3 folder structure generation"""
    # Load templates for the specified language
    templates = load_prompt_templates(language)
    
    # Check both singular and plural forms for backward compatibility
    prompt_templates = templates.get("folder_structure_prompts", templates.get("folder_structure_prompt", {}))
    
    # Get system prompt template
    system_prompt = prompt_templates.get("level3_system_prompt", prompt_templates.get("system_prompt", prompt_templates.get("system")))
    if not system_prompt:
        logging.critical("Level 3 system prompt template not found in language configuration")
        sys.exit(1)
    
    # Get level 3 user prompt template
    level3_prompt_template = prompt_templates.get("level3_folders_prompt", prompt_templates.get("level3_user_prompt", prompt_templates.get("level3")))
    if not level3_prompt_template:
        logging.critical("Level 3 folders prompt template not found in language configuration")
        sys.exit(1)
    
    # Get description for level 2 folder
    l2_description = l2_folder_data.get("description", l2_folder_name)
    
    # Get role format template for the language
    role_formatted = ""
    if role:
        role_templates = templates.get("role_templates", {}).get(language, {})
        role_format = role_templates.get("role_format", " for {role}")
        role_formatted = role_format.format(role=role)
    
    # Create parameters for the template
    params = {
        "industry": industry,
        "l1_folder_name": l1_folder_name,
        "l2_folder_name": l2_folder_name,
        "l1_description": l1_description,
        "l2_description": l2_description,
        "role": role if role else "",
        "role_text": role_formatted
    }
    
    # Compose the prompt - the template already includes the instruction to return only JSON
    prompt = compose_prompt(level3_prompt_template, params, date_range, language, system_prompt)
    
    return prompt

def get_level3_files_prompt(
    industry: str,
    l2_folder_name: str,
    l2_folder_data: dict,
    l1_description: str,
    l1_folder_name: str,
    language: str,
    role: Optional[str] = None,
    date_range: Optional[Tuple[date, date]] = None
) -> str:
    """Create prompt for level 3 files generation"""
    # Load templates for the specified language
    templates = load_prompt_templates(language)
    
    # Check both singular and plural forms for backward compatibility
    prompt_templates = templates.get("folder_structure_prompts", templates.get("folder_structure_prompt", {}))
    
    # Get system prompt template
    system_prompt = prompt_templates.get("level3_files_system_prompt", prompt_templates.get("system_prompt", prompt_templates.get("system")))
    if not system_prompt:
        logging.warning("Level 3 files system prompt template not found, using default system prompt")
        system_prompt = prompt_templates.get("system_prompt", prompt_templates.get("system"))
    
    # Get level 3 files prompt template
    level3_files_template = prompt_templates.get("level3_files_prompt")
    if not level3_files_template:
        logging.critical("Level 3 files prompt template not found in language configuration")
        sys.exit(1)
    
    # Get description for level 2 folder
    l2_description = l2_folder_data.get("description", l2_folder_name)
    
    # Get folder structure for context
    folder_structure = ""
    if "folders" in l2_folder_data and isinstance(l2_folder_data["folders"], dict):
        folder_names = list(l2_folder_data["folders"].keys())
        folder_structure = ", ".join(folder_names)
    
    # Get role format template for the language
    role_formatted = ""
    if role:
        role_templates = templates.get("role_templates", {}).get(language, {})
        role_format = role_templates.get("role_format", " for {role}")
        role_formatted = role_format.format(role=role)
    
    # Create parameters for the template
    params = {
        "industry": industry,
        "l1_folder_name": l1_folder_name,
        "l2_folder_name": l2_folder_name,
        "l1_description": l1_description,
        "l2_description": l2_description,
        "folder_structure": folder_structure,
        "role": role if role else "",
        "role_text": role_formatted
    }
    
    # Compose the prompt
    prompt = compose_prompt(level3_files_template, params, date_range, language, system_prompt)
    
    return prompt

def generate_level1_folders(industry: str, language: str = "en-US", role: str = None, model: str = None) -> Dict:
    """Generate a folder structure for a given industry"""
    logging.info(f"Calling LLM to generate Level 1 folder structure for {industry} industry...")
    
    # Import here to avoid circular imports
    from src.llm_utils import call_ollama_json
    
    # Set up Ollama URL and model
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    
    # Log configuration
    logging.info(f"Using Ollama URL: {ollama_url}")
    if model:
        logging.info(f"Using Ollama model: {model} (temperature: 0.7)")
    else:
        logging.info(f"Using Ollama model: llama3 (temperature: 0.7)")
    
    # Load language templates for prompts
    language_key = get_normalized_language_key(language)
    templates = load_prompt_templates(language_key)
    json_format_instructions = templates.get("json_format_instructions", {})
    
    # Get the JSON generation prompt template
    l1_prompt_template = json_format_instructions.get("level1_folders_prompt", "")
    if not l1_prompt_template:
        logging.error(f"Missing level1_folders_prompt template for language {language_key}")
        logging.error(f"Available keys in json_format_instructions: {list(json_format_instructions.keys())}")
        return None
    
    # Create a role text snippet for prompt insertion using language-specific formatting
    role_formatted = ""
    if role:
        role_templates = templates.get("role_templates", {}).get(language_key, {})
        role_format = role_templates.get("role_format", " for {role}")
        role_formatted = role_format.format(role=role)
    
    # Format the JSON generation prompt
    try:
        logging.debug(f"Formatting prompt template with industry={industry}, role_formatted={role_formatted}")
        json_prompt = l1_prompt_template.format(
            industry=industry,
            role_text=role_formatted,
            date_range=""
        )
        logging.debug(f"Formatted prompt: {json_prompt[:200]}...")
    except Exception as e:
        logging.error(f"Error formatting prompt template: {e}")
        logging.error(f"Template: {l1_prompt_template}")
        return None
    
    # Define expected keys
    expected_keys = ['industry', 'folders']
    
    try:
        # Call the LLM to generate the folder structure
        logging.info("Sending request to LLM...")
        response = call_ollama_json(
            json_prompt,
            model=model,
            ollama_url=ollama_url,
            structure_hint="industry,folders",
            expected_keys=expected_keys,
            language=language
        )
        
        logging.debug(f"Response from LLM: {response}")
        
        # If no response or missing folders, use fallback
        if not response:
            logging.error("No valid response from LLM for folder structure.")
            return None
            
        # Validate response has folders and they're a dict
        if "folders" not in response or not isinstance(response["folders"], dict) or not response["folders"]:
            logging.error("Response is missing valid 'folders' key or has empty folders.")
            logging.error(f"Response: {response}")
            return None
            
        # Further validate each folder has a description
        for folder_name, folder_data in response.get("folders", {}).items():
            if not isinstance(folder_data, dict) or "description" not in folder_data:
                logging.error(f"Folder {folder_name} is missing a description or has invalid structure.")
                return None
        
        logging.info(f"Successfully generated folder structure with {len(response.get('folders', {}))} folders")
        return response
    except Exception as e:
        logging.error(f"Error generating level 1 folders: {e}")
        logging.exception("Exception details:")
        return None

def sanitize_path(path_str: str) -> str:
    """Sanitize filenames and folder names (especially for non-ASCII chars)"""
    # Replace problematic characters with underscores
    sanitized = path_str.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    
    # Limit filename length to 100 characters
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:100-len(ext)] + ext
    
    return sanitized 