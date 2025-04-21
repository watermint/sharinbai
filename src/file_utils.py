#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import random
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
import traceback

# Import from local modules
from src.language_utils import get_normalized_language_key, load_prompt_templates, get_date_format, get_translation

def sanitize_path(path_str: str) -> str:
    """Sanitize filenames and folder names (especially for non-ASCII chars)"""
    # Replace problematic characters with underscores
    sanitized = path_str.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    
    # Limit filename length to 100 characters
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:100-len(ext)] + ext
    
    return sanitized

def suggest_alternative_filenames(file_name: str, existing_files: list) -> str:
    """Suggest a single alternative filename when a filename clashes"""
    try:
        # Get the base name without extension
        base_name = Path(file_name).stem
        extension = Path(file_name).suffix
        
        # Try adding numbers to the filename
        for i in range(1, 100):
            alternative = f"{base_name}_{i}{extension}"
            if alternative not in existing_files:
                return alternative
        
        # If all numbered alternatives are taken, try different extensions
        supported_extensions = ['.docx', '.xlsx', '.pdf', '.txt', '.jpg', '.png']
        for ext in supported_extensions:
            if ext != extension:
                alternative = f"{base_name}{ext}"
                if alternative not in existing_files:
                    return alternative
                    
        # Last resort: random suffix
        import random
        random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))
        return f"{base_name}_{random_suffix}{extension}"
    except Exception as e:
        logging.error(f"Error suggesting alternative filename: {e}")
        return f"{base_name}_alt{extension}"

def generate_random_files(count: int, industry: str, language: str, folder_level: int = 3, folder_name: str = "") -> List[Dict[str, str]]:
    """Generate random files appropriate for the folder using LLM, with mathematical distribution"""
    files = []
    language_key = get_normalized_language_key(language)
    
    # Get industry data if available
    templates = load_prompt_templates(language_key)
    
    # Apply mathematical distribution for file count based on folder level
    # Level 1 folders should have very few or no files
    # Level 2 folders should also be minimal
    if folder_level == 1:
        # Level 1: 94% chance of 0 files, 4% chance of 1 file, 2% chance of 2 files
        probabilities = [0.94, 0.04, 0.02]
        possible_counts = [0, 1, 2]
        adjusted_count = random.choices(possible_counts, weights=probabilities, k=1)[0]
        logging.info(f"Level 1 folder: Adjusted file count from {count} to {adjusted_count} based on distribution")
        count = adjusted_count
    elif folder_level == 2:
        # Level 2: 80% chance of 0 files, 15% chance of 1-2 files, 5% chance of original count
        rand_val = random.random()
        if rand_val < 0.8:
            adjusted_count = 0
        elif rand_val < 0.95:  # 0.8 + 0.15
            adjusted_count = random.randint(1, 2)
        else:
            adjusted_count = count
        logging.info(f"Level 2 folder: Adjusted file count from {count} to {adjusted_count} based on distribution")
        count = adjusted_count
    
    # If count is 0, return empty list
    if count == 0:
        return files
    
    # Supported file types
    file_types = ["docx", "xlsx", "pdf", "txt"]
    
    # Check if we should use LLM to generate file names
    from src.llm_utils import call_ollama_json
    
    # Get file generation template from localized resources if available
    file_generation_template = templates.get("file_generation_prompts", {}).get("random_files_prompt")
    
    # Use the folder name if provided, otherwise use the industry name
    display_folder_name = folder_name if folder_name else industry
    
    # Create a prompt for the LLM to generate file names
    if file_generation_template:
        # Use localized template if available
        try:
            prompt = file_generation_template.format(
                count=count,
                folder_name=display_folder_name,
                industry=industry,
                folder_level=folder_level
            )
            logging.info(f"Using localized file generation prompt for language: {language_key}")
        except KeyError as e:
            logging.error(f"KeyError in file generation template: {e}")
            # Fall back to default English prompt
            prompt = f"""Generate {count} appropriate file names for a folder named "{display_folder_name}" in the {industry} industry.
Each file should have a name, type, and description.
Only use these file types: docx, xlsx, pdf, or txt.

Please respond with a JSON object with an array of file objects in this format:
{{
  "files": [
    {{
      "name": "filename.ext",
      "type": "file extension (docx, xlsx, pdf, or txt)",
      "description": "Brief description of the file content"
    }},
    ...
  ]
}}

For level {folder_level} folders, files should be relevant to {display_folder_name} and related to the industry.
Do not include file names with "template", "sample", "example", or placeholder text.
Filenames should be specific, practical, and realistic.
"""
            logging.info("Falling back to English prompt due to template error")
    else:
        # Fall back to default English prompt
        prompt = f"""Generate {count} appropriate file names for a folder named "{display_folder_name}" in the {industry} industry.
Each file should have a name, type, and description.
Only use these file types: docx, xlsx, pdf, or txt.

Please respond with a JSON object with an array of file objects in this format:
{{
  "files": [
    {{
      "name": "filename.ext",
      "type": "file extension (docx, xlsx, pdf, or txt)",
      "description": "Brief description of the file content"
    }},
    ...
  ]
}}

For level {folder_level} folders, files should be relevant to {display_folder_name} and related to the industry.
Do not include file names with "template", "sample", "example", or placeholder text.
Filenames should be specific, practical, and realistic.
"""
        logging.info("Using default English file generation prompt (no localized template available)")

    try:
        # Call LLM to generate file names
        model = os.getenv("OLLAMA_MODEL", "gemma3:12b")
        response = call_ollama_json(
            prompt=prompt,
            model=model,
            structure_hint="files array with name, type, and description fields",
            max_attempts=3,
            language=language
        )
        
        if response and "files" in response and isinstance(response["files"], list) and len(response["files"]) > 0:
            logging.info(f"LLM successfully generated {len(response['files'])} file names")
            return response["files"][:count]  # Only take the requested count
    except Exception as e:
        logging.error(f"Error calling LLM to generate file names: {e}")
    
    # Fallback to basic generation if LLM fails
    logging.info("Fallback to basic file name generation")
    
    # Generate files based on type
    for i in range(count):
        # Select a file type
        file_type = random.choice(file_types)
        
        # Create filename based on industry context
        if file_type == "docx":
            file_name = f"{industry}_{i+1}.{file_type}"
            description = f"Document for {industry}"
        elif file_type == "xlsx":
            # Excel files often include dates
            current_date = datetime.now()
            date_str = current_date.strftime("%Y-%m")
            file_name = f"{industry}_{date_str}.{file_type}"
            description = f"Spreadsheet with {industry} data"
        elif file_type == "pdf":
            file_name = f"{industry}_v{random.randint(1,3)}.{file_type}"
            description = f"PDF document for {industry}"
        elif file_type == "txt":
            file_name = f"{industry}_notes.{file_type}"
            description = f"Text notes for {industry} reference"
        
        # Avoid empty keywords in filename
        file_name = file_name.replace("__", "_")
        
        # Add to files list
        files.append({
            "name": file_name,
            "type": file_type,
            "description": description
        })
    
    return files

def create_directory_structure_recursive(
    industry: str,
    structure: Dict,
    current_dir: Path,
    folders_to_populate: Set,
    language: str = "en-US",
    role: str = None,
    file_examples: Dict[str, str] = None,
    date_range: Tuple[date, date] = None,
    current_path: str = "",
    parent_context: str = "",
    created_folder_paths: Set[str] = None,
    current_depth: int = 0,
    max_depth: int = 3,
    min_depth: int = 1,
    exceed_max_depth_files: bool = False
) -> None:
    """Recursively create a directory structure based on the provided structure"""
    # Initialize set of created folder paths if None
    if created_folder_paths is None:
        created_folder_paths = set()
    
    try:
        # Create the current directory if it doesn't exist
        try:
            # Ensure the current directory exists
            if not current_dir.exists():
                current_dir.mkdir(parents=True, exist_ok=True)
                logging.info(f"Created directory: {current_dir}")
            elif not current_dir.is_dir():
                logging.error(f"Path exists but is not a directory: {current_dir}")
                return
        except PermissionError:
            logging.error(f"Permission denied: Cannot create directory {current_dir}")
            return
        except OSError as e:
            logging.error(f"Failed to create directory {current_dir}: {e}")
            return
        
        # Skip processing if we've exceeded the maximum depth
        if current_depth > max_depth:
            logging.info(f"Maximum depth {max_depth} reached at {current_dir}, not processing subfolders")
            
            # Only create files if asked to exceed max depth
            if not exceed_max_depth_files:
                return

        # Check for folder metadata
        is_timeseries = structure.get("timeseries", False)
        file_type_limitation = structure.get("file_type_limitation", None)
        folder_description = structure.get("description", "")
        
        # Create metadata dictionary for folder
        folder_metadata = {}
        if is_timeseries:
            folder_metadata["timeseries"] = True
        if file_type_limitation:
            folder_metadata["file_type_limitation"] = file_type_limitation
        
        # Add the current folder to the list of folders to populate with files
        if current_depth >= min_depth:
            # Convert folder_metadata to string to make it hashable
            metadata_str = str(folder_metadata) if folder_metadata else ""
            
            # Add folder to the set of folders to populate with files
            folders_to_populate.add((
                str(current_dir),
                current_path or str(current_dir.name),
                folder_description,
                industry,
                metadata_str,
                parent_context
            ))
            logging.info(f"Marked folder for file generation: {current_dir}")
        
        # Process subfolders at this level
        folders = structure.get("folders", {})
        
        # Process subdirectories
        if isinstance(folders, dict) and folders:
            for folder_name, folder_data in folders.items():
                if isinstance(folder_data, dict):
                    # Sanitize folder name
                    safe_folder_name = sanitize_path(folder_name)
                    
                    # Create folder path
                    folder_path = current_dir / safe_folder_name
                    
                    logging.info(f"Processing subfolder: {safe_folder_name} at {current_dir}")
                    
                    # Add to set of created folder paths
                    full_path_str = str(folder_path)
                    if full_path_str not in created_folder_paths:
                        created_folder_paths.add(full_path_str)
                        
                        # Get folder description or default
                        folder_description = folder_data.get("description", folder_name)
                        
                        # Build new path description
                        new_path = f"{current_path} > {folder_name}" if current_path else folder_name
                        
                        # Add folder description as context
                        new_context = folder_description
                        
                        # Create the folder
                        try:
                            if not folder_path.exists():
                                folder_path.mkdir(parents=True, exist_ok=True)
                                logging.info(f"Created subfolder: {folder_path}")
                            elif not folder_path.is_dir():
                                logging.error(f"Path exists but is not a directory: {folder_path}")
                                continue
                        except PermissionError:
                            logging.error(f"Permission denied: Cannot create directory {folder_path}")
                            continue
                        except OSError as e:
                            logging.error(f"Failed to create directory {folder_path}: {e}")
                            continue
                        
                        # Recursively process this folder
                        create_directory_structure_recursive(
                            industry,
                            folder_data,
                            folder_path,
                            folders_to_populate,
                            language,
                            role,
                            file_examples,
                            date_range,
                            new_path,
                            new_context,
                            created_folder_paths,
                            current_depth + 1,
                            max_depth,
                            min_depth,
                            exceed_max_depth_files
                        )
                    else:
                        logging.warning(f"Skipping duplicate folder path: {full_path_str}")
                else:
                    logging.error(f"Invalid folder data for {folder_name}: expected dict but got {type(folder_data)}")
        elif folders:
            logging.error(f"Invalid folders structure: expected dict but got {type(folders)}")
    except Exception as e:
        logging.error(f"Error in create_directory_structure_recursive: {e}")
        raise

def create_directory_structure(industry: str, structure: Dict, current_dir: Path, language: str = "en-US", role: str = None, file_examples: Dict[str, str] = None, date_range: Tuple[date, date] = None) -> None:
    """Wrapper function for create_directory_structure_recursive to maintain backward compatibility"""
    logging.info(f"Creating directory structure for {industry} at {current_dir}")
    
    # Ensure current_dir is a Path object
    if isinstance(current_dir, str):
        current_dir = Path(current_dir)
    
    # Create the root directory if it doesn't exist
    try:
        if not current_dir.exists():
            current_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created root directory: {current_dir}")
        elif not current_dir.is_dir():
            logging.error(f"Path exists but is not a directory: {current_dir}")
            return
    except Exception as e:
        logging.error(f"Failed to create root directory {current_dir}: {e}")
        return
    
    # Validate the structure first
    if not isinstance(structure, dict):
        logging.error(f"Invalid structure: expected dict but got {type(structure)}")
        logging.error(f"Structure: {structure}")
        return
    
    # Validate that folders exist in the structure
    if "folders" not in structure or not isinstance(structure["folders"], dict) or not structure["folders"]:
        logging.error(f"Invalid or empty folders in structure")
        logging.error(f"Structure keys: {list(structure.keys()) if isinstance(structure, dict) else 'N/A'}")
        return
    
    # Initialize folders_to_populate
    folders_to_populate = set()
    
    # Call the recursive function to create the directory structure
    create_directory_structure_recursive(
        industry=industry,
        structure=structure,
        current_dir=current_dir,
        folders_to_populate=folders_to_populate,
        language=language,
        role=role,
        file_examples=file_examples,
        date_range=date_range,
        min_depth=1
    )
    
    # Debug info about folders to populate
    if folders_to_populate:
        logging.info(f"Folders to populate with files: {len(folders_to_populate)}")
        for folder_data in list(folders_to_populate)[:5]:  # Log first 5 folders for debugging
            dir_path, folder_name, description, _, metadata, _ = folder_data
            logging.info(f"Folder in queue for file generation: {dir_path} (Metadata: {metadata})")
    else:
        logging.warning("No folders to populate with files")
        return
    
    # Initialize counters
    folders_populated = 0
    
    # Process the folders that need to be populated with files
    for folder_data in folders_to_populate:
        try:
            # Unpack the tuple
            dir_path, folder_name, description, industry, metadata_str, parent_context = folder_data
            
            # Convert metadata string back to dictionary if needed
            metadata = {}
            if metadata_str and metadata_str.startswith("{") and metadata_str.endswith("}"):
                try:
                    # Basic parsing of the string representation of the dictionary
                    if "timeseries" in metadata_str:
                        metadata["timeseries"] = True
                    if "file_type_limitation" in metadata_str:
                        # Extract the file type limitation value
                        import re
                        match = re.search(r"'file_type_limitation':\s*'([^']*)'", metadata_str)
                        if match:
                            metadata["file_type_limitation"] = match.group(1)
                except Exception as e:
                    logging.error(f"Error parsing metadata string: {e}")
            
            # Import function here to avoid circular imports
            from src.document_generators import generate_folder_files
            
            # Log folder file generation attempt
            logging.info(f"Generating files for folder: {dir_path}")
            
            # Generate files based on folder metadata
            num_files = generate_folder_files(
                dir_path, 
                folder_name, 
                description, 
                industry, 
                language, 
                role, 
                file_examples, 
                date_range,
                metadata
            )
            
            # Increment folder count if successful
            if num_files > 0:
                folders_populated += 1
                logging.info(f"Successfully populated folder: {dir_path} with {num_files} files")
            else:
                logging.warning(f"Failed to populate folder with files: {dir_path}")
        except Exception as e:
            logging.error(f"Error populating folder {folder_data[0]}: {e}")
            logging.error(f"Error details: {traceback.format_exc()}")
    
    logging.info(f"Directory structure created at: {current_dir}")
    logging.info(f"Total folders populated with files: {folders_populated}")
    logging.info("Generation complete!") 