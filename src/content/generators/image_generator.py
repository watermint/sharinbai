"""
Image file generator
"""

import logging
import os
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

from src.content.generators.base_generator import BaseGenerator

class ImageGenerator(BaseGenerator):
    """Generator for image files"""
    
    def generate(self, directory: str, filename: str, description: str,
                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate placeholder image content.
        
        Args:
            directory: Target directory for the file
            filename: Name of the file to create
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if file was successfully created, False otherwise
        """
        if not IMAGE_AVAILABLE:
            logging.error("Pillow package is not available. Please install it with: pip install Pillow")
            return False
            
        file_path = self.get_file_path(directory, filename)
        
        try:
            # Create a placeholder image with text
            width, height = 800, 600
            background_color = (240, 240, 240)
            text_color = (100, 100, 100)
            
            # Create image with background color
            img = Image.new('RGB', (width, height), background_color)
            draw = ImageDraw.Draw(img)
            
            # Try to find font
            font_path = os.path.join('resources', 'NotoSans-VariableFont_wdth,wght.ttf')
            try:
                font = ImageFont.truetype(font_path, 24)
            except Exception:
                # Use default font if custom font not available
                font = ImageFont.load_default()
            
            # Draw border
            draw.rectangle([(20, 20), (width-20, height-20)], outline=(200, 200, 200), width=2)
            
            # Draw title
            title = f"Placeholder Image: {description}"
            draw.text((width/2, 100), title, font=font, fill=text_color, anchor="mm")
            
            # Draw additional info
            info_text = [
                f"Industry: {industry}",
                f"Language: {language}"
            ]
            if role:
                info_text.append(f"Role: {role}")
                
            # Draw each line of text
            for i, text in enumerate(info_text):
                draw.text((width/2, 200 + i*40), text, font=font, fill=text_color, anchor="mm")
            
            # Save image
            img.save(file_path)
            return True
        except Exception as e:
            logging.error(f"Failed to create image {filename}: {e}")
            return False 