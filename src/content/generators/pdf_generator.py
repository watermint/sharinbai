"""
PDF document generator
"""

import logging
import os
from typing import Optional, Dict

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from src.content.generators.base_generator import BaseGenerator

class PdfGenerator(BaseGenerator):
    """Generator for PDF documents (.pdf)"""
    
    # Language to font mapping
    LANGUAGE_FONTS: Dict[str, str] = {
        # Asian languages with specific fonts
        'ja': 'NotoSansJP-VariableFont_wght.ttf',  # Japanese
        'ko': 'NotoSansKR-VariableFont_wght.ttf',  # Korean
        'zh': 'NotoSansSC-VariableFont_wght.ttf',  # Simplified Chinese
        'zh-tw': 'NotoSansTC-VariableFont_wght.ttf',  # Traditional Chinese
        
        # European languages using base NotoSans
        'en': 'NotoSans-VariableFont_wdth,wght.ttf',  # English
        'en-gb': 'NotoSans-VariableFont_wdth,wght.ttf',  # British English
        'de': 'NotoSans-VariableFont_wdth,wght.ttf',  # German
        'fr': 'NotoSans-VariableFont_wdth,wght.ttf',  # French
        'es': 'NotoSans-VariableFont_wdth,wght.ttf',  # Spanish
        'it': 'NotoSans-VariableFont_wdth,wght.ttf',  # Italian
        'pt': 'NotoSans-VariableFont_wdth,wght.ttf',  # Portuguese
        'nl': 'NotoSans-VariableFont_wdth,wght.ttf',  # Dutch
        'pl': 'NotoSans-VariableFont_wdth,wght.ttf',  # Polish
        'ru': 'NotoSans-VariableFont_wdth,wght.ttf',  # Russian
        'uk': 'NotoSans-VariableFont_wdth,wght.ttf',  # Ukrainian
        'vi': 'NotoSans-VariableFont_wdth,wght.ttf',  # Vietnamese
    }
    
    def __init__(self, llm_client):
        """Initialize the PDF generator"""
        super().__init__(llm_client)
        if PDF_AVAILABLE:
            # Register fonts for all supported languages
            for lang, font_file in self.LANGUAGE_FONTS.items():
                font_path = os.path.join('resources', font_file)
                try:
                    if lang in ['ja', 'ko', 'zh', 'zh-tw']:
                        font_name = f'NotoSans{lang.upper()}'
                    else:
                        font_name = 'NotoSans'
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                except Exception as e:
                    logging.warning(f"Failed to register {font_name} font: {e}")
    
    def generate(self, directory: str, filename: str, description: str,
                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate PDF document content.
        
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
        if not PDF_AVAILABLE:
            logging.error("reportlab package is not available. Please install it with: pip install reportlab")
            return False
            
        file_path = self.get_file_path(directory, filename)
        
        # Create prompt for document content
        prompt = self.create_prompt(description, industry, language, role, "PDF document")
        
        # Generate content using LLM
        content = self.llm_client.get_completion(prompt)
        
        if not content:
            logging.error(f"Failed to generate content for {filename}")
            return False
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Create custom styles for supported languages
            if language in self.LANGUAGE_FONTS:
                if language in ['ja', 'ko', 'zh', 'zh-tw']:
                    font_name = f'NotoSans{language.upper()}'
                else:
                    font_name = 'NotoSans'
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Title'],
                    fontName=font_name,
                    fontSize=16,
                    leading=20
                )
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontName=font_name,
                    fontSize=12,
                    leading=16
                )
            else:
                title_style = styles['Title']
                normal_style = styles['Normal']
            
            story = []
            
            # Add title
            story.append(Paragraph(description, title_style))
            story.append(Spacer(1, 12))
            
            # Add content paragraphs
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    story.append(Paragraph(paragraph.strip(), normal_style))
                    story.append(Spacer(1, 6))
            
            # Build the PDF
            doc.build(story)
            return True
        except Exception as e:
            logging.error(f"Failed to create PDF document {filename}: {e}")
            return False 