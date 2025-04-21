#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from datetime import date

from PIL import Image, ImageDraw, ImageFont

# Import from local modules
from src.language_utils import register_font

def create_image_file(file_path: str, file_name: str, description: str, industry: str, language: str = "en-US", role: str = None, file_examples: Dict[str, str] = None, date_range: Tuple[date, date] = None, model: str = None) -> bool:
    """Create a simple image file with placeholder text based on the description"""
    try:
        # Set up image parameters
        width, height = 800, 600
        background_color = (255, 255, 255)
        text_color = (0, 0, 0)
        
        # Create a blank image with white background
        image = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(image)
        
        # Try to register a font for the language
        font_name, font_path = register_font(language)
        
        try:
            if font_path:
                font_title = ImageFont.truetype(str(font_path), 36)
                font_text = ImageFont.truetype(str(font_path), 20)
            else:
                # Use a default font if no custom font available
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()
        except Exception as e:
            logging.warning(f"Could not load font: {e}. Using default font instead.")
            # Use a default font
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()
        
        # Draw the file name as title
        title_text = file_name
        # Get title dimensions for centering
        draw.text((width // 2, 50), title_text, fill=text_color, font=font_title, anchor="mt")
        
        # Draw description
        description_lines = []
        words = description.split()
        current_line = ""
        
        # Break description into lines
        for word in words:
            test_line = current_line + " " + word if current_line else word
            # Check if adding this word exceeds the width
            try:
                text_width = draw.textlength(test_line, font=font_text)
                if text_width < width - 100:  # Leave margins
                    current_line = test_line
                else:
                    description_lines.append(current_line)
                    current_line = word
            except AttributeError:
                # Fallback for older Pillow versions that don't have textlength
                if font_text.getsize(test_line)[0] < width - 100:
                    current_line = test_line
                else:
                    description_lines.append(current_line)
                    current_line = word
        
        # Add the last line
        if current_line:
            description_lines.append(current_line)
        
        # Draw description lines
        y_position = 150
        for line in description_lines:
            try:
                draw.text((width // 2, y_position), line, fill=text_color, font=font_text, anchor="mt")
            except TypeError:
                # Fallback for older Pillow versions that don't support anchor
                text_size = font_text.getsize(line)
                text_x = (width - text_size[0]) // 2
                draw.text((text_x, y_position), line, fill=text_color, font=font_text)
            y_position += 30
        
        # Draw industry info
        industry_text = f"Industry: {industry}"
        y_position = height - 100
        try:
            draw.text((width // 2, y_position), industry_text, fill=text_color, font=font_text, anchor="mt")
        except TypeError:
            # Fallback for older Pillow versions
            text_size = font_text.getsize(industry_text)
            text_x = (width - text_size[0]) // 2
            draw.text((text_x, y_position), industry_text, fill=text_color, font=font_text)
            
        # Draw role if available
        if role:
            role_formatted = f"Role: {role}"
            y_position += 30
            try:
                draw.text((width // 2, y_position), role_formatted, fill=text_color, font=font_text, anchor="mt")
            except TypeError:
                # Fallback for older Pillow versions
                text_size = font_text.getsize(role_formatted)
                text_x = (width - text_size[0]) // 2
                draw.text((text_x, y_position), role_formatted, fill=text_color, font=font_text)
        
        # Save the image
        full_file_path = os.path.join(file_path, file_name)
        image.save(full_file_path)
        logging.info(f"Created image file: {full_file_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating image file {file_name}: {e}")
        return False 