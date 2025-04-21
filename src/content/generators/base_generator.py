"""
Base generator for file content generation
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

from src.config.language_utils import get_translation
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
                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate file content.
        
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
                     role: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """
        Create a prompt for the LLM based on the parameters.
        
        Args:
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            file_type: Type of file (optional)
            
        Returns:
            Formatted prompt for the LLM
            
        Raises:
            SystemExit: If the required language resource is missing
        """
        # Get the prompt template from language resources
        prompt_template = get_translation("prompts.content_generation", language, None)
        
        # Raise an error if no prompt template is found for this language
        if not prompt_template:
            error_msg = f"No prompt template found for language '{language}'"
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        
        # Get role and file type parts from resources
        role_template = get_translation("prompts.role_context", language, None)
        file_type_template = get_translation("prompts.file_type_context", language, None)
        
        if not role_template or not file_type_template:
            error_msg = f"Missing prompt components for language '{language}'"
            print(error_msg, file=sys.stderr)
            sys.exit(1)
            
        # Format the conditional parts
        role_context = role_template.format(role=role) if role else ""
        file_type_context = file_type_template.format(file_type=file_type) if file_type else ""
        
        # Return the complete formatted prompt
        return prompt_template.format(
            description=description,
            industry=industry,
            role_context=role_context,
            language=language,
            file_type_context=file_type_context
        ) 