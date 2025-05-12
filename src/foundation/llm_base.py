"""
Base LLM client interface for different LLM providers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union

class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def get_completion(self, prompt: str, system: Optional[str] = None, 
                      max_attempts: int = 3) -> Optional[str]:
        """
        Get a text completion from the model.
        
        Args:
            prompt: The prompt to send to the model
            system: Optional system message
            max_attempts: Maximum number of retry attempts
            
        Returns:
            Model completion text or None if the request failed
        """
        pass
    
    @abstractmethod
    def get_json_completion(self, prompt: str, system_prompt: Optional[str] = None, 
                           max_attempts: int = 3, language: str = "en") -> Optional[Dict[str, Any]]:
        """
        Get a JSON formatted completion from the model.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system message
            max_attempts: Maximum number of retry attempts
            language: Language code for translations
            
        Returns:
            Parsed JSON response or None if parsing failed
        """
        pass
