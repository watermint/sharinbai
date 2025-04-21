"""
Text file generator
"""

import logging
from typing import Optional

from src.content.generators.base_generator import BaseGenerator


class TextGenerator(BaseGenerator):
    """Generator for text files"""
    
    def generate(self, directory: str, filename: str, description: str,
                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate text file content.
        
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
        file_path = self.get_file_path(directory, filename)
        
        # Create prompt for text content
        prompt = self.create_prompt(description, industry, language, role, "text")
        
        # Generate content using LLM
        content = self.llm_client.get_completion(prompt)
        
        if not content:
            logging.error(f"Failed to generate content for {filename}")
            return False
            
        # Write content to file
        return self.file_manager.write_text_file(file_path, content) 