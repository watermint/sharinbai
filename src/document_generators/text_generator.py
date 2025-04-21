#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, Tuple, Any, Optional
from datetime import date
from pathlib import Path

# Import from local modules
from src.language_utils import get_normalized_language_key, load_prompt_templates

def create_text_file(file_path: str, file_name: str, description: str, industry: str, language: str = "en-US", role: str = None, file_examples: Dict[str, str] = None, date_range: Tuple[date, date] = None, model: str = None) -> bool:
    """Create a simple text file with the provided description"""
    try:
        # Construct full file path
        full_file_path = os.path.join(file_path, file_name)
        
        # Get template for text content
        templates = load_prompt_templates(get_normalized_language_key(language))
        ui_strings = templates.get("ui_strings", {})
        
        # Generate simple content based on file name and description
        content = f"# {file_name}\n\n"
        content += f"{description}\n\n"
        content += f"Industry: {industry}\n"
        if role:
            content += f"Role: {role}\n"
        
        # Create the file
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"Created file: {full_file_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating text file {file_name}: {e}")
        return False 