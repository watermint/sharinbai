#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse
import sys
from src.config.settings import Settings
from src.config.logging_config import setup_logging
from src.config.language_utils import (
    get_default_language,
    get_normalized_language_key,
    get_supported_languages,
    is_language_supported
)
from src.structure.folder_generator import FolderGenerator

def main():
    parser = argparse.ArgumentParser(description='Generate industry-specific folder structures with placeholder files')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    def add_common_args(subparser):
        subparser.add_argument('--industry', '-i', type=str, required=True, help='Industry for the folder structure')
        subparser.add_argument('--path', '-p', type=str, default='./out', help='Path where to create the folder structure')
        subparser.add_argument('--language', '-l', type=str, default=get_default_language(), help='Language for the folder structure')
        subparser.add_argument('--model', '-m', type=str, default='llama3', help='Ollama model to use')
        subparser.add_argument('--role', '-r', type=str, default=None, help='Specific role within the industry')
        subparser.add_argument('--ollama-url', type=str, default=None, help='URL for the Ollama API server.')
    all_parser = subparsers.add_parser('all', help='Create folder structure and generate all files')
    add_common_args(all_parser)
    file_parser = subparsers.add_parser('file', help='Generate or update files in existing folder structure')
    add_common_args(file_parser)
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
    settings = Settings().from_args(vars(args))
    setup_logging(settings.log_level, settings.output_path)
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
