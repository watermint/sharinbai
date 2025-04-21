#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse
import sys
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Set

# Import modular components
from src.logging_config import setup_logging
from src.language_utils import (
    get_default_language,
    get_normalized_language_key,
    load_language_mapping,
    load_prompt_templates,
    get_supported_languages,
    is_language_supported,
    get_available_language_files,
    get_translation
)
from src.llm_utils import call_ollama_json
from src.file_utils import sanitize_path
from src.folder_structure import (
    generate_level1_folders,
    get_level2_folder_structure_prompt,
    get_level3_folder_structure_prompt,
    get_level3_files_prompt
)
from src.document_generators import generate_file_content

def main():
    """
    Main entry point for Sharinbai - directory structure generator
    """
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    parser.add_argument('--industry', '-i', type=str, help='Industry for the folder structure')
    parser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
    parser.add_argument('--language', '-l', type=str, default=get_default_language(), help='Language for the folder structure')
    parser.add_argument('--model', '-m', type=str, default='llama3', help='Ollama model to use')
    parser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Logging level')
    parser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
    parser.add_argument('--list-languages', action='store_true', help='List supported languages based on available resource files')
    parser.add_argument('--test-language-utils', action='store_true', help='Test language utilities')
    args = parser.parse_args()

    # Ensure the path is an absolute path
    args.path = os.path.abspath(args.path)
    
    # Setup logging
    setup_logging(args.log_level, args.path)
    
    # Just list supported languages if requested
    if args.list_languages:
        supported = get_supported_languages()
        if supported:
            print(get_translation("ui_strings.supported_languages_header", "en", "Supported languages:"))
            for lang in sorted(supported):
                print(f"  {lang}")
        else:
            print(get_translation("ui_strings.no_language_files", "en", "No language resource files found."))
        sys.exit(0)
    
    # Test language utilities if requested
    if args.test_language_utils:
        print("Testing language utilities:")
        
        # Test loading language mapping
        print("\nLanguage Mapping:")
        mapping = load_language_mapping()
        if "language_templates" in mapping:
            print(f"- Language templates available: {', '.join(k for k in mapping['language_templates'] if k != 'default')}")
            print(f"- Default language: {mapping['language_templates'].get('default', 'Not specified')}")
        else:
            print("- Language templates not found in mapping")
        
        # Test get_default_language
        default_lang = get_default_language()
        print(f"\nDefault language: {default_lang}")
        
        # Test get_supported_languages
        supported = get_supported_languages()
        print(f"\nSupported languages: {', '.join(supported)}")
        
        # Test language normalization
        test_langs = ["english", "ja", "Japanese", "EN-US", "en_GB", "zh-Hans"]
        print("\nLanguage normalization:")
        for lang in test_langs:
            normalized = get_normalized_language_key(lang)
            print(f"- {lang} -> {normalized}")
            print(f"  Supported: {is_language_supported(lang)}")
        
        # Test available language files
        print("\nAvailable language files:")
        lang_files = get_available_language_files()
        for lang, path in lang_files.items():
            print(f"- {lang}: {path}")
        
        sys.exit(0)
    
    # Ensure industry is provided if not just testing
    if not args.industry:
        logging.error(get_translation("ui_strings.error_messages.industry_required", "en", "--industry argument is required"))
        parser.print_help()
        sys.exit(1)
    
    # Normalize language
    normalized_language = get_normalized_language_key(args.language)
    if normalized_language != args.language:
        logging.info(get_translation("ui_strings.language_normalized", "en", 
                                    "Normalized language from {from_lang} to {to_lang}").format(
                                    from_lang=args.language, to_lang=normalized_language))
    
    # Show warning if language is not fully supported
    if not is_language_supported(normalized_language):
        logging.warning(get_translation("ui_strings.language_not_supported", "en", 
                                       "Language '{language}' is not directly supported. Using best available match.").format(
                                       language=normalized_language))
    
    # Create the target directory if it doesn't exist
    try:
        os.makedirs(args.path, exist_ok=True)
        logging.info(f"Created output directory: {args.path}")
    except Exception as e:
        logging.error(f"Failed to create output directory {args.path}: {e}")
        sys.exit(1)
    
    # Get folder structure from LLM
    try:
        # Generate hierarchical folder structure
        logging.info(f"Generating hierarchical folder structure for {args.industry} industry")
        
        # Create formatted directory name using {{industry}}_{{role}} format
        formatted_dir_name = f"{args.industry}_{args.role if args.role else 'general'}"
        formatted_dir_name = sanitize_path(formatted_dir_name)
        
        # Convert path to Path object and set the target directory with the formatted name
        base_dir = Path(args.path)
        target_dir = base_dir / formatted_dir_name
        
        # Create root directory
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created root directory: {target_dir}")
        
        # Get the level 1 folder structure first, then process level 2 and 3 for each folder separately
        level1_structure = generate_level1_folders(
            industry=args.industry,
            language=normalized_language,
            role=args.role,
            model=args.model
        )
        
        if not level1_structure or not isinstance(level1_structure, dict) or "folders" not in level1_structure:
            logging.error("Failed to get a valid level 1 folder structure from the model.")
            sys.exit(1)
            
        # Create level 1 folders one by one
        logging.info(f"Creating level 1 folders for {args.industry}")
        level1_folders = list(level1_structure["folders"].keys())
        for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
            # Create level 1 folder
            l1_folder_path = target_dir / sanitize_path(l1_folder_name)
            if not l1_folder_path.exists():
                l1_folder_path.mkdir(parents=True, exist_ok=True)
                logging.info(f"Created level 1 folder: {l1_folder_name}")
        
        # Now process each level 1 folder to add level 2 and 3 folders
        for i, l1_folder_name in enumerate(level1_folders):
            if l1_folder_name not in level1_structure["folders"]:
                logging.warning(f"Folder {l1_folder_name} not found in structure, skipping")
                continue
                
            l1_folder_data = level1_structure["folders"][l1_folder_name]
            if not isinstance(l1_folder_data, dict) or "description" not in l1_folder_data:
                logging.warning(f"Invalid data for folder {l1_folder_name}, skipping")
                continue
                
            logging.info(f"Processing level 2 folders for {l1_folder_name} ({i+1}/{len(level1_folders)})")
            l1_folder_path = target_dir / sanitize_path(l1_folder_name)
            
            # Get level 2 folders structure
            level2_structure = call_ollama_json(
                prompt=get_level2_folder_structure_prompt(
                    industry=args.industry,
                    l1_folder_name=l1_folder_name,
                    l1_description=l1_folder_data.get("description", ""),
                    language=normalized_language,
                    role=args.role
                ),
                model=args.model,
                ollama_url=args.ollama_url,
                structure_hint=f"The JSON should have a structure with keys like 'folders'",
                max_attempts=5,
                language=normalized_language
            )
            
            if not level2_structure or not isinstance(level2_structure, dict) or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping")
                continue
                
            # Create level 2 folders one by one and process level 3 immediately
            for l2_folder_name, l2_folder_data in level2_structure["folders"].items():
                if not isinstance(l2_folder_data, dict) or "description" not in l2_folder_data:
                    logging.warning(f"Invalid data for level 2 folder {l2_folder_name}, skipping")
                    continue
                    
                # Create level 2 folder
                l2_folder_path = l1_folder_path / sanitize_path(l2_folder_name)
                if not l2_folder_path.exists():
                    l2_folder_path.mkdir(parents=True, exist_ok=True)
                    logging.info(f"Created level 2 folder: {l1_folder_name}/{l2_folder_name}")
                
                # Get and create level 3 folders
                logging.info(f"Processing level 3 folders for {l1_folder_name}/{l2_folder_name}")
                level3_structure = call_ollama_json(
                    prompt=get_level3_folder_structure_prompt(
                        industry=args.industry,
                        l2_folder_name=l2_folder_name,
                        l2_folder_data=l2_folder_data,
                        l1_description=l1_folder_data.get("description", ""),
                        l1_folder_name=l1_folder_name,
                        language=normalized_language,
                        role=args.role
                    ),
                    model=args.model,
                    ollama_url=args.ollama_url,
                    structure_hint=f"The JSON should have a structure with keys like 'folders'",
                    max_attempts=5,
                    language=normalized_language
                )
                
                if not level3_structure or not isinstance(level3_structure, dict) or "folders" not in level3_structure:
                    logging.warning(f"Failed to get valid level 3 structure for {l1_folder_name}/{l2_folder_name}, skipping")
                    continue
                
                # Create level 3 folders one by one
                for l3_folder_name, l3_folder_data in level3_structure["folders"].items():
                    if not isinstance(l3_folder_data, dict) or "description" not in l3_folder_data:
                        logging.warning(f"Invalid data for level 3 folder {l3_folder_name}, skipping")
                        continue
                        
                    # Create level 3 folder
                    l3_folder_path = l2_folder_path / sanitize_path(l3_folder_name)
                    if not l3_folder_path.exists():
                        l3_folder_path.mkdir(parents=True, exist_ok=True)
                        logging.info(f"Created level 3 folder: {l1_folder_name}/{l2_folder_name}/{l3_folder_name}")
                
                # Generate files for level 2 folder
                logging.info(f"Generating files for {l1_folder_name}/{l2_folder_name}")
                level3_files = call_ollama_json(
                    prompt=get_level3_files_prompt(
                        industry=args.industry,
                        l2_folder_name=l2_folder_name,
                        l2_folder_data=l2_folder_data,
                        l1_description=l1_folder_data.get("description", ""),
                        l1_folder_name=l1_folder_name,
                        language=normalized_language,
                        role=args.role
                    ),
                    model=args.model,
                    ollama_url=args.ollama_url,
                    structure_hint=f"The JSON should have a structure with keys like 'files'",
                    max_attempts=5,
                    language=normalized_language
                )
                
                if "files" in level3_files and isinstance(level3_files["files"], list):
                    logging.info(f"Creating {len(level3_files['files'])} files in {l1_folder_name}/{l2_folder_name}")
                    
                    # Create each file immediately
                    for file_info in level3_files["files"]:
                        try:
                            if not isinstance(file_info, dict) or "name" not in file_info:
                                continue
                                
                            filename = file_info["name"]
                            description = file_info.get("description", "")
                            
                            # Generate file content
                            success = generate_file_content(
                                str(l2_folder_path),
                                filename,
                                description,
                                args.industry,
                                normalized_language,
                                args.role,
                                None,
                                None,
                                args.model
                            )
                            
                            if success:
                                logging.info(f"Created file: {l1_folder_name}/{l2_folder_name}/{filename}")
                        except Exception as e:
                            logging.error(f"Error creating file {file_info.get('name', 'unknown')}: {e}")
            
            logging.info(f"Completed processing {l1_folder_name} ({i+1}/{len(level1_folders)})")
        
        logging.info(f"Folder structure creation complete")
        
    except Exception as e:
        logging.critical(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
