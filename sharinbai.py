#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse
import sys
import os
from pathlib import Path
from src.config.settings import Settings
from src.config.logging_config import setup_logging
from src.config.language_utils import (
    get_default_language,
    get_normalized_language_key,
    get_supported_languages,
    is_language_supported,
    get_available_language_files
)
from src.structure.folder_generator import FolderGenerator
from src.content.file_manager import FileManager

def main():
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    def add_common_args(subparser):
        subparser.add_argument('--industry', '-i', type=str, help='Industry for the folder structure (can be omitted if .metadata.json exists)')
        subparser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
        subparser.add_argument('--language', '-l', type=str, help='Language for the folder structure (can be omitted if .metadata.json exists)')
        subparser.add_argument('--model', '-m', type=str, default='llama3', help='Ollama model to use')
        subparser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry (can be omitted if .metadata.json exists)')
        subparser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
        subparser.add_argument('--short', action='store_true', help='Enable short mode (max 5 items)')
    all_parser = subparsers.add_parser('all', help='Create folder structure and generate all files')
    add_common_args(all_parser)
    file_parser = subparsers.add_parser('file', help='Generate or update files in existing folder structure')
    add_common_args(file_parser)
    structure_parser = subparsers.add_parser('structure', help='Create only folder structure without generating files')
    add_common_args(structure_parser)
    subparsers.add_parser('list-languages', help='List supported languages')
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
    
    # Initialize settings from args with default language
    settings = Settings().from_args(vars(args))
    
    # Set up logging early to capture any issues
    setup_logging(settings.log_level, settings.output_path)
    
    # If working with existing structure, try to retrieve metadata
    if args.command in ['file'] or (args.command in ['all', 'structure'] and Path(settings.output_path).exists()):
        target_dir = Path(settings.output_path)
        metadata_path = target_dir / ".metadata.json"
        
        if metadata_path.exists():
            file_manager = FileManager()
            metadata = file_manager.read_json_file(str(metadata_path))
            if metadata:
                # Update industry from metadata if not provided by args
                if not args.industry and 'industry' in metadata:
                    settings.industry = metadata['industry']
                    logging.info(f"Retrieved industry '{settings.industry}' from metadata")
                
                # Update role from metadata if not provided by args
                if not args.role and 'role' in metadata:
                    settings.role = metadata['role']
                    logging.info(f"Retrieved role '{settings.role}' from metadata")
                
                # Update language from metadata if not provided by args
                if not args.language and 'language' in metadata:
                    settings.language = metadata['language']
                    logging.info(f"Retrieved language '{settings.language}' from metadata")
    
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
            role = input("Please enter a specific role within the industry (optional, press Enter to skip): ")
            if role.strip():
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
