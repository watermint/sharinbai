#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import traceback
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from datetime import date

# Import PDF libraries
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

# Import from local modules
from src.language_utils import get_normalized_language_key, get_date_format, register_font

def create_pdf_document(file_path: str, file_name: str, description: str, industry: str, language: str = "en-US", role: str = None, file_examples: Dict[str, str] = None, date_range: Tuple[date, date] = None, model: str = None) -> bool:
    """Create a PDF document with content appropriate for the file name and description"""
    try:
        # Register appropriate font
        font_alias, font_path = register_font(language)
        
        # If register_font returns None, it means the required font was not found
        if font_alias is None:
            logging.error(f"NotoSans font for language {language} not found. Using default font.")
            font_alias = "Helvetica"
        
        # Create PDF document
        full_file_path = os.path.join(file_path, file_name)
        doc = SimpleDocTemplate(
            full_file_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Define custom style names to avoid conflicts
        heading0_name = 'CustomHeading0'
        heading1_name = 'CustomHeading1'
        heading2_name = 'CustomHeading2'
        normal_name = 'CustomNormal'
        bullet_name = 'CustomBullet'
        
        # Use the registered font or fallback to Helvetica
        try:
            # Add custom styles with unique names
            styles.add(ParagraphStyle(name=heading0_name, fontName=font_alias, fontSize=18, leading=22, spaceAfter=12))
            styles.add(ParagraphStyle(name=heading1_name, fontName=font_alias, fontSize=16, leading=20, spaceAfter=10))
            styles.add(ParagraphStyle(name=heading2_name, fontName=font_alias, fontSize=14, leading=18, spaceAfter=8))
            styles.add(ParagraphStyle(name=normal_name, fontName=font_alias, fontSize=10, leading=14, spaceAfter=6))
            styles.add(ParagraphStyle(name=bullet_name, fontName=font_alias, fontSize=10, leading=14, leftIndent=20, bulletIndent=10, spaceAfter=6))
        except Exception as font_error:
            # If there are issues with the custom font, fall back to Helvetica
            logging.warning(f"Error using custom font: {font_error}. Falling back to Helvetica.")
            styles.add(ParagraphStyle(name=heading0_name, fontName='Helvetica-Bold', fontSize=18, leading=22, spaceAfter=12))
            styles.add(ParagraphStyle(name=heading1_name, fontName='Helvetica-Bold', fontSize=16, leading=20, spaceAfter=10))
            styles.add(ParagraphStyle(name=heading2_name, fontName='Helvetica-Bold', fontSize=14, leading=18, spaceAfter=8))
            styles.add(ParagraphStyle(name=normal_name, fontName='Helvetica', fontSize=10, leading=14, spaceAfter=6))
            styles.add(ParagraphStyle(name=bullet_name, fontName='Helvetica', fontSize=10, leading=14, leftIndent=20, bulletIndent=10, spaceAfter=6))
        
        # Create content
        content = []
        
        # Add title
        content.append(Paragraph(file_name, styles[heading1_name]))
        
        # Add description
        content.append(Paragraph(description, styles[normal_name]))
        content.append(Spacer(1, 12))
        
        # Add industry info
        content.append(Paragraph("Overview", styles[heading1_name]))
        content.append(Paragraph(f"Industry: {industry}", styles[normal_name]))
        
        # Add role if available
        if role:
            content.append(Paragraph(f"Role: {role}", styles[normal_name]))
        
        # Add date range if available
        if date_range:
            start_date_str = get_date_format(date_range[0], "prompt", language)
            end_date_str = get_date_format(date_range[1], "prompt", language)
            content.append(Paragraph(f"Period: {start_date_str} - {end_date_str}", styles[normal_name]))
        
        # Add main content sections based on file name
        file_name_lower = file_name.lower()
        
        # Add default content
        content.append(Spacer(1, 12))
        content.append(Paragraph("Introduction", styles[heading1_name]))
        content.append(Paragraph(f"This document provides information about {description}.", styles[normal_name]))
        
        content.append(Spacer(1, 12))
        content.append(Paragraph("Content", styles[heading1_name]))
        content.append(Paragraph(f"This is a sample PDF document for {industry}.", styles[normal_name]))
        
        # Add some bullet points
        content.append(Paragraph("Key points:", styles[normal_name]))
        for i in range(1, 4):
            content.append(Paragraph(f"• Point {i}: Important information about {industry}", styles[bullet_name]))
        
        # Add conclusion
        content.append(Spacer(1, 12))
        content.append(Paragraph("Conclusion", styles[heading1_name]))
        content.append(Paragraph(f"This document was created as part of a file structure for {industry}.", styles[normal_name]))
            
        # Generate the PDF
        doc.build(content)
        logging.info(f"Created PDF document: {full_file_path}")
        return True
    except Exception as e:
        logging.critical(f"Error creating PDF document {file_path}/{file_name}: {e}")
        logging.critical(f"Error details: {traceback.format_exc()}")
        return False 