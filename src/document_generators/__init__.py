#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import random
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from datetime import date

# Import all document generators
from src.document_generators.docx_generator import (
    create_docx_document, 
    create_report_document,
    create_proposal_document,
    create_manual_document,
    create_minutes_document,
    create_memo_document,
    create_generic_document
)
from src.document_generators.xlsx_generator import create_excel_workbook
from src.document_generators.pdf_generator import create_pdf_document
from src.document_generators.text_generator import create_text_file
from src.document_generators.image_generator import create_image_file

def generate_file_content(file_path: str, file_name: str, description: str, industry: str, language: str = "en-US", role: str = None, file_examples: Dict[str, str] = None, date_range: Tuple[date, date] = None, model: str = None) -> bool:
    """Generate content for a file based on its type"""
    logging.info(f"Generating content for file: {file_path}")
    
    # Verify the directory path exists
    if not os.path.exists(file_path):
        try:
            os.makedirs(file_path, exist_ok=True)
            logging.info(f"Created directory: {file_path}")
        except PermissionError:
            logging.error(f"Permission denied: Cannot create directory {file_path}")
            return False
        except OSError as e:
            logging.error(f"Failed to create directory {file_path}: {e}")
            return False
    elif not os.path.isdir(file_path):
        logging.error(f"Path exists but is not a directory: {file_path}")
        return False
    
    # Construct the full file path by joining directory and filename
    full_file_path = os.path.join(file_path, file_name)
    
    # Check if the target file already exists
    if os.path.exists(full_file_path):
        logging.warning(f"File already exists: {full_file_path}")
        try:
            # Remove the existing file so we can recreate it with updated content
            os.remove(full_file_path)
            logging.info(f"Removed existing file: {full_file_path}")
        except (PermissionError, OSError) as e:
            logging.error(f"Failed to remove existing file {full_file_path}: {e}")
            return False
    
    # Get file extension
    file_ext = Path(file_name).suffix.lower()
    
    # Load language templates
    from src.language_utils import get_normalized_language_key, load_prompt_templates
    templates = load_prompt_templates(language)
    ui_strings = templates.get("ui_strings", {})
    error_messages = ui_strings.get("error_messages", {})
    
    # Language normalization
    language_key = get_normalized_language_key(language)

    # Supported file types
    supported_extensions = ['.docx', '.xlsx', '.pdf', '.txt', '.jpg', '.png']

    # Choose appropriate method based on file extension
    try:
        result = False
        
        # Log file generation attempt with details
        logging.info(f"Attempting to create file: {full_file_path}")
        logging.info(f"File type: {file_ext}")
        logging.info(f"Description: {description[:50]}..." if len(description) > 50 else f"Description: {description}")
        
        if file_ext == '.docx':
            result = create_docx_document(file_path, file_name, description, industry, language, role, file_examples, date_range, model)
        elif file_ext == '.xlsx':
            result = create_excel_workbook(file_path, file_name, description, industry, language, role, file_examples, date_range, model)
        elif file_ext == '.pdf':
            result = create_pdf_document(file_path, file_name, description, industry, language, role, file_examples, date_range, model)
        elif file_ext == '.txt':
            result = create_text_file(file_path, file_name, description, industry, language, role, file_examples, date_range, model)
        elif file_ext in ['.jpg', '.png']:
            result = create_image_file(file_path, file_name, description, industry, language, role, file_examples, date_range, model)
        else:
            # Unknown extension - convert to a supported format
            new_ext = '.txt'  # Default to .txt as it's the simplest
            new_file_name = str(Path(file_name).with_suffix(new_ext))
            
            # Log the change
            unsupported_ext_msg = error_messages.get("unsupported_extension", "Unsupported file extension: {ext}. Using {new_ext} instead.")
            try:
                log_message = unsupported_ext_msg.format(ext=file_ext, new_ext=new_ext)
            except KeyError:
                # Fallback if the template is missing required keys
                log_message = f"Unsupported file extension: {file_ext}. Using {new_ext} instead."
            logging.warning(log_message)
            
            # Create a simple text file with information about the conversion
            try:
                with open(os.path.join(file_path, new_file_name), 'w', encoding='utf-8') as f:
                    fallback_template = ui_strings.get("fallback_file_template", "# {file_name}\n\n{description}\n\nIndustry: {industry}\nRole: {role}\n")
                    try:
                        fallback_content = fallback_template.format(
                            file_name=file_name,
                            description=description,
                            industry=industry,
                            role=role or ui_strings.get("not_specified", "Not specified")
                        )
                    except KeyError:
                        # Fallback if template has missing keys
                        fallback_content = f"# {file_name}\n\n{description}\n\nIndustry: {industry}\nRole: {role or 'Not specified'}"
                        
                    # Add a note about the conversion
                    conversion_note = f"\nNOTE: This file was originally requested with unsupported extension '{file_ext}' and has been converted to a text file.\n"
                    f.write(fallback_content + conversion_note)
                
                logging.info(f"Created text fallback file for unsupported extension: {os.path.join(file_path, new_file_name)}")
                result = True
            except PermissionError:
                fallback_error_msg = error_messages.get("fallback_file_error", "Failed to create fallback file: {error}")
                try:
                    logging.critical(fallback_error_msg.format(error="Permission denied"))
                except KeyError:
                    logging.critical(f"Failed to create fallback file: Permission denied")
                result = False
            except Exception as e2:
                fallback_error_msg = error_messages.get("fallback_file_error", "Failed to create fallback file: {error}")
                try:
                    logging.critical(fallback_error_msg.format(error=e2))
                except KeyError:
                    logging.critical(f"Failed to create fallback file: {e2}")
                result = False
        
        # Check if file was actually created
        if result:
            final_path = full_file_path
            if file_ext not in supported_extensions:
                final_path = os.path.join(file_path, str(Path(file_name).with_suffix('.txt')))
                
            if os.path.exists(final_path):
                logging.info(f"Verified file was created: {final_path}")
            else:
                logging.warning(f"Function reported success but file doesn't exist: {final_path}")
                result = False
        
        return result
    except PermissionError:
        logging.critical(f"Permission denied: Cannot create file {full_file_path}")
        return False
    except OSError as e:
        logging.critical(f"File system error when generating content for {full_file_path}: {e}")
        return False
    except Exception as e:
        import traceback
        logging.critical(f"Error generating content for {full_file_path}: {e}")
        logging.critical(f"Traceback: {traceback.format_exc()}")
        return False 

def generate_folder_files(
    dir_path: str, 
    folder_name: str, 
    description: str, 
    industry: str, 
    language: str = "en-US", 
    role: Optional[str] = None, 
    file_examples: Optional[Dict[str, str]] = None, 
    date_range: Optional[Tuple[date, date]] = None, 
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Generate files for a specific folder based on folder metadata and description
    
    Args:
        dir_path: Directory path where files should be created
        folder_name: Name of the folder
        description: Description of the folder
        industry: Industry context
        language: Language code
        role: Role context
        file_examples: Example files to use as templates
        date_range: Date range for time-sensitive content
        metadata: Additional folder metadata
        
    Returns:
        Number of files successfully created
    """
    logging.info(f"Generating files for folder: {dir_path}")
    
    if metadata is None:
        metadata = {}
    
    # Determine number of files to generate (2-5 is a reasonable default)
    num_files = random.randint(2, 5)
    
    # Check if this folder has specific file type limitations
    file_type_limitation = metadata.get("file_type_limitation", None)
    
    # Determine folder level by counting path segments
    # More sophisticated approaches could use information from the structure
    path_parts = dir_path.strip('/').split('/')
    # Assume the industry folder is at level 0, so adjust accordingly
    folder_level = len(path_parts) - 1
    if folder_level < 1:
        folder_level = 1
    
    logging.info(f"Detected folder level: {folder_level} for {dir_path}")
    
    # Generate random files for this folder
    from src.file_utils import generate_random_files
    files_to_create = generate_random_files(
        count=num_files, 
        industry=industry, 
        language=language,
        folder_level=folder_level,
        folder_name=folder_name
    )
    
    # If there's a file type limitation, filter the files
    if file_type_limitation:
        filtered_files = []
        for file_data in files_to_create:
            if file_data["type"] == file_type_limitation:
                filtered_files.append(file_data)
        
        # If filtering removed all files, generate at least one of the required type
        if not filtered_files and files_to_create:
            # Create at least one file of the required type
            from src.file_utils import generate_random_files
            special_files = generate_random_files(1, industry, language, folder_level, folder_name)
            for file_data in special_files:
                file_data["type"] = file_type_limitation
                filtered_files.append(file_data)
        
        files_to_create = filtered_files
    
    # Get existing files in the directory to avoid duplicates
    try:
        existing_files = os.listdir(dir_path)
    except:
        existing_files = []
    
    # Create a unique folder identifier based on folder name for differentiating files
    # Use the last part of the path if folder_name is not provided
    if not folder_name:
        folder_name = os.path.basename(dir_path)
    
    folder_hash = abs(hash(folder_name)) % 1000  # Create a short numeric hash of the folder name
    
    # Create each file
    files_created = 0
    for idx, file_data in enumerate(files_to_create):
        try:
            # Extract file data
            original_file_name = file_data["name"]
            file_desc = file_data["description"]
            
            # Make the filename unique by adding folder hash
            base_name, extension = os.path.splitext(original_file_name)
            file_name = f"{base_name}_{folder_hash}{extension}"
            
            # If file already exists, make it more unique with index
            if file_name in existing_files:
                file_name = f"{base_name}_{folder_hash}_{idx}{extension}"
            
            # If still exists (unlikely), use the suggest_alternative_filenames function
            if file_name in existing_files:
                from src.file_utils import suggest_alternative_filenames
                file_name = suggest_alternative_filenames(file_name, existing_files)
            
            # Add to existing files list to prevent duplicates in the same batch
            existing_files.append(file_name)
            
            # Generate the file content
            success = generate_file_content(
                dir_path, 
                file_name, 
                file_desc, 
                industry, 
                language, 
                role, 
                file_examples, 
                date_range
            )
            
            if success:
                files_created += 1
                logging.info(f"Successfully created file: {os.path.join(dir_path, file_name)}")
            else:
                logging.warning(f"Failed to create file: {os.path.join(dir_path, file_name)}")
        except Exception as e:
            logging.error(f"Error creating file {file_data.get('name', 'unknown')}: {e}")
    
    logging.info(f"Created {files_created} files in folder {dir_path}")
    return files_created 