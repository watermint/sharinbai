"""
Base generator for file content generation
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

from src.config.language_utils import get_translation, LocalizedTemplateNotFoundError
from src.content.file_manager import FileManager
from src.foundation.llm_client import OllamaClient


class BaseGenerator(ABC):
    """Base abstract class for all content generators"""
    
    def __init__(self, llm_client: OllamaClient):
        """
        Initialize the base generator.
        
        Args:
            llm_client: LLM client for content generation
        """
        self.llm_client = llm_client
        self.file_manager = FileManager()
    
    @abstractmethod
    def generate(self, directory: str, filename: str, description: str,
                industry: str, language: str, role: Optional[str] = None,
                date_range_str: Optional[str] = None) -> bool:
        """
        Generate file content.
        
        Args:
            directory: Target directory for the file
            filename: Name of the file to create
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            date_range_str: Date range information (optional)
            
        Returns:
            True if file was successfully created, False otherwise
        """
        pass
    
    def get_file_path(self, directory: str, filename: str) -> str:
        """
        Get the full file path.
        
        Args:
            directory: Target directory
            filename: Filename
            
        Returns:
            Full file path
        """
        return os.path.join(directory, self.file_manager.sanitize_path(filename))
    
    def create_prompt(self, description: str, industry: str, language: str, 
                     role: Optional[str] = None, file_type: Optional[str] = None,
                     date_range_str: Optional[str] = None) -> str:
        """
        Create a prompt for the LLM based on the parameters.
        
        Args:
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            file_type: Type of file (optional)
            date_range_str: Date range information (optional)
            
        Returns:
            Formatted prompt for the LLM
            
        Raises:
            LocalizedTemplateNotFoundError: If required language resources are missing
        """
        # Get the prompt template from language resources
        prompt_template = get_translation("prompts.content_generation", language)
        
        # Get role and file type parts from resources
        role_template = get_translation("prompts.role_context", language)
        file_type_template = get_translation("prompts.file_type_context", language)
            
        # Format the conditional parts
        role_context = role_template.format(role=role) if role else ""
        file_type_context = file_type_template.format(file_type=file_type) if file_type else ""
        
        # Create the base prompt
        prompt = prompt_template.format(
            description=description,
            industry=industry,
            role_context=role_context,
            language=language,
            file_type_context=file_type_context
        )
        
        # Append date range information if provided
        if date_range_str:
            prompt = f"{prompt}\n\n{date_range_str}"
            
        return prompt 