"""
Content generator for creating various file formats
"""

import logging
from pathlib import Path
import os
import datetime
from typing import Dict, Any, Optional, List, Union

from src.foundation.llm_client import OllamaClient
from src.content.file_manager import FileManager
from src.content.generators import (
    TextGenerator,
    DocxGenerator,
    PdfGenerator,
    XlsxGenerator,
    ImageGenerator
)

class ContentGenerator:
    """Generates content for various file formats"""
    
    # Maximum number of timeseries folders allowed at each level
    MAX_TIMESERIES_FOLDERS = 5
    
    def __init__(self, model: str = "llama3", ollama_url: Optional[str] = None):
        """
        Initialize the content generator.
        
        Args:
            model: Model name to use for content generation
            ollama_url: URL for the Ollama API server
        """
        self.llm_client = OllamaClient(model, ollama_url)
        self.file_manager = FileManager()
        
        # Initialize the generators
        self.generators = {
            "txt": TextGenerator(self.llm_client),
            "docx": DocxGenerator(self.llm_client),
            "pdf": PdfGenerator(self.llm_client),
            "xlsx": XlsxGenerator(self.llm_client),
            "image": ImageGenerator(self.llm_client)
        }
        
    def generate_file(self, directory: str, filename: str, description: str,
                     industry: str, language: str, role: Optional[str] = None, 
                     purpose: Optional[str] = None) -> bool:
        """
        Generate a file with the appropriate content.
        
        Args:
            directory: Target directory for the file
            filename: Name of the file to create
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            purpose: Purpose of the folder (optional)
            
        Returns:
            True if file was successfully created, False otherwise
        """
        # Ensure the directory exists
        if not self.file_manager.ensure_directory(directory):
            return False
            
        # Get file extension to determine generator
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip(".").lower()
        
        # Handle timeseries folder purpose if specified
        if purpose == "timeseries":
            # Use date-based naming convention for files in timeseries folders
            filename = self._format_timeseries_filename(filename, ext)
        
        # Save file metadata separately
        file_metadata = {
            "filename": filename,
            "description": description,
            "industry": industry,
            "language": language,
            "role": role,
            "extension": ext,
            "purpose": purpose
        }
        
        metadata_dir = os.path.join(directory, ".metadata")
        self.file_manager.ensure_directory(metadata_dir)
        metadata_filename = f"{self.file_manager.sanitize_path(filename)}.json"
        metadata_path = os.path.join(metadata_dir, metadata_filename)
        self.file_manager.write_json_file(metadata_path, file_metadata)
        
        # Use appropriate generator
        if ext in self.generators:
            return self.generators[ext].generate(
                directory, filename, description, industry, language, role
            )
        elif ext in ["png", "jpg"]:
            return self.generators["image"].generate(
                directory, filename, description, industry, language, role
            )
        else:
            # Default to text generator for unknown extensions
            logging.warning(f"No specific generator for extension '{ext}', using text generator")
            return self.generators["txt"].generate(
                directory, filename, description, industry, language, role
            ) 
            
    def _format_timeseries_filename(self, filename: str, ext: str) -> str:
        """
        Format a filename for timeseries folders using a date-based naming convention.
        
        Args:
            filename: Original filename
            ext: File extension
            
        Returns:
            Formatted filename with date prefix
        """
        today = datetime.datetime.now()
        date_prefix = today.strftime("%Y-%m-%d_")
        
        # Remove extension from filename
        name_without_ext = os.path.splitext(filename)[0]
        
        # Add date prefix if not already present
        if not name_without_ext.startswith(date_prefix):
            return f"{date_prefix}{filename}"
        
        return filename
    
    def is_timeseries_limit_reached(self, parent_dir: str) -> bool:
        """
        Check if the maximum number of timeseries folders has been reached.
        
        Args:
            parent_dir: Parent directory to check
            
        Returns:
            True if limit reached, False otherwise
        """
        # Count folders with timeseries purpose in metadata
        timeseries_count = 0
        
        try:
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path):
                    metadata_path = os.path.join(item_path, ".metadata.json")
                    if os.path.exists(metadata_path):
                        metadata = self.file_manager.read_json_file(metadata_path)
                        if metadata and metadata.get("purpose") == "timeseries":
                            timeseries_count += 1
            
            return timeseries_count >= self.MAX_TIMESERIES_FOLDERS
        except Exception as e:
            logging.error(f"Error checking timeseries folder limit: {e}")
            # Default to False on error
            return False 