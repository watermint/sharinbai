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
    is_language_supported
)
from src.structure.folder_generator import FolderGenerator
from src.content.file_manager import FileManager

def main():
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    def add_common_args(subparser):
        subparser.add_argument('--industry', '-i', type=str, help='Industry for the folder structure (can be omitted if .metadata.json exists)')
        subparser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
        subparser.add_argument('--language', '-l', type=str, default=get_default_language(), help='Language for the folder structure')
        subparser.add_argument('--model', '-m', type=str, default='llama3', help='Ollama model to use')
        subparser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry (can be omitted if .metadata.json exists)')
        subparser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
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
    
    # Initialize settings from args
    settings = Settings().from_args(vars(args))
    
    # Set up logging early to capture any issues
    setup_logging(settings.log_level, settings.output_path)
    
    # If working with existing structure, try to retrieve industry/role from metadata
    if args.command in ['file'] and not args.industry:
        target_dir = Path(settings.output_path)
        metadata_path = target_dir / ".metadata.json"
        
        if metadata_path.exists():
            file_manager = FileManager()
            metadata = file_manager.read_json_file(str(metadata_path))
            if metadata:
                if 'industry' in metadata:
                    settings.industry = metadata['industry']
                    logging.info(f"Retrieved industry '{settings.industry}' from metadata")
                if 'role' in metadata:
                    settings.role = metadata['role']
                    logging.info(f"Retrieved role '{settings.role}' from metadata")
    
    # Ask for industry/role if not provided and needed for new structure
    if args.command in ['all', 'structure'] and not settings.industry:
        industry = input("Please enter the industry for the folder structure: ")
        if not industry.strip():
            logging.error("Industry is required but not provided")
            sys.exit(1)
        settings.industry = industry
        
        role = input("Please enter a specific role within the industry (optional, press Enter to skip): ")
        if role.strip():
            settings.role = role
    
    # Ensure we have industry for all commands
    if not hasattr(settings, 'industry') or not settings.industry:
        logging.error("Industry is required but not provided. Use --industry/-i option or ensure .metadata.json exists.")
        sys.exit(1)
    
    settings.language = get_normalized_language_key(settings.language)
    if settings.language != args.language:
        logging.info(f"Normalized language from {args.language} to {settings.language}")
    if not is_language_supported(settings.language):
        logging.warning(f"Language '{settings.language}' is not directly supported. Using best available match.")
    
    folder_generator = FolderGenerator(settings.model, settings.ollama_url)
    try:
        if args.command == 'all':
            logging.info(f"Generating complete folder structure for {settings.industry} industry")
            success = folder_generator.generate_all(
                settings.output_path, 
                settings.industry,
                settings.role,
                settings.language
            )
        elif args.command == 'file':
            logging.info(f"Generating files only for {settings.industry} industry")
            success = folder_generator.generate_files_only(
                settings.output_path,
                settings.industry,
                settings.role,
                settings.language
            )
        elif args.command == 'structure':
            logging.info(f"Creating folder structure only for {settings.industry} industry")
            success = folder_generator.generate_structure_only(
                settings.output_path,
                settings.industry,
                settings.role,
                settings.language
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
