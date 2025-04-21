"""
Content generator for creating various file formats
"""

import logging
from pathlib import Path
import os
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
                     industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate a file with the appropriate content.
        
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
        # Ensure the directory exists
        if not self.file_manager.ensure_directory(directory):
            return False
            
        # Get file extension to determine generator
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip(".").lower()
        
        # Use appropriate generator
        if ext in self.generators:
            return self.generators[ext].generate(
                directory, filename, description, industry, language, role
            )
        elif ext in ["png", "jpg", "jpeg", "webp", "gif"]:
            return self.generators["image"].generate(
                directory, filename, description, industry, language, role
            )
        else:
            # Default to text generator for unknown extensions
            logging.warning(f"No specific generator for extension '{ext}', using text generator")
            return self.generators["txt"].generate(
                directory, filename, description, industry, language, role
            ) 