"""
PDF document generator
"""

import logging
import os
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from src.content.generators.base_generator import BaseGenerator

class PdfGenerator(BaseGenerator):
    """Generator for PDF documents (.pdf)"""
    
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
            story = []
            
            # Add title
            title_style = styles['Title']
            story.append(Paragraph(description, title_style))
            story.append(Spacer(1, 12))
            
            # Add content paragraphs
            normal_style = styles['Normal']
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