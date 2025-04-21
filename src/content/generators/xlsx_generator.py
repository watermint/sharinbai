"""
Excel spreadsheet generator
"""

import logging
import json
import os
from typing import Optional, Dict, List, Any

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

from src.content.generators.base_generator import BaseGenerator
from src.config.language_utils import get_translation

class XlsxGenerator(BaseGenerator):
    """Generator for Excel spreadsheets (.xlsx)"""
    
    def generate(self, directory: str, filename: str, description: str,
                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate Excel spreadsheet content.
        
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
        if not XLSX_AVAILABLE:
            logging.error("openpyxl package is not available. Please install it with: pip install openpyxl")
            return False
            
        file_path = self.get_file_path(directory, filename)
        
        # Load system message from language resources
        try:
            # Get system message for structured output
            system_message = get_translation("content_generation.xlsx_generation", language, None)
            if not system_message:
                logging.error(f"Missing 'content_generation.xlsx_generation' in language resources for {language}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to load system message from language resources for '{language}': {e}")
            return False
        
        # Create prompt for spreadsheet content
        prompt = self.create_prompt(description, industry, language, role, "Excel spreadsheet")
        if not prompt:
            logging.error(f"Failed to create prompt for {filename} with language '{language}'")
            return False
        
        # Generate structured content using LLM
        content = self.llm_client.get_json_completion(
            prompt=prompt,
            system=system_message
        )
        
        if not content or "sheets" not in content:
            logging.error(f"Failed to generate valid spreadsheet content for {filename}")
            return False
        
        try:
            # Create Excel workbook
            wb = openpyxl.Workbook()
            # Remove default sheet
            default_sheet = wb.active
            wb.remove(default_sheet)
            
            # Process each sheet
            for sheet_data in content["sheets"]:
                # Create sheet
                sheet_name = sheet_data.get("name", "Sheet")
                sheet = wb.create_sheet(title=sheet_name)
                
                # Add headers
                headers = sheet_data.get("headers", [])
                for col_idx, header in enumerate(headers, start=1):
                    cell = sheet.cell(row=1, column=col_idx, value=header)
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                
                # Add data rows
                rows = sheet_data.get("data", [])
                for row_idx, row_data in enumerate(rows, start=2):
                    for col_idx, value in enumerate(row_data, start=1):
                        sheet.cell(row=row_idx, column=col_idx, value=value)
                
                # Auto-adjust column widths
                for col_idx, _ in enumerate(headers, start=1):
                    # Approximate width calculation
                    sheet.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 15
            
            # Save workbook
            wb.save(file_path)
            return True
        except Exception as e:
            logging.error(f"Failed to create Excel document {filename}: {e}")
            return False 