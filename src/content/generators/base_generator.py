"""
Base generator for file content generation
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

from src.foundation.llm_client import OllamaClient
from src.content.file_manager import FileManager

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
        """
        role_context = f" for a {role}" if role else ""
        file_type_context = f" The output should be in {file_type} format." if file_type else ""
        
        return (
            f"Generate content for a {description} in the {industry} industry{role_context}. "
            f"The content should be in {language} language.{file_type_context} "
            f"Be concise and professional."
        ) 