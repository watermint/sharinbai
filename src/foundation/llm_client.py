"""
LLM client for communication with Ollama API
"""

import json
import logging
import os
import re
import requests
import time
from typing import Dict, Any, Optional, List, Union

from src.config.settings import Settings
from src.config import get_translation
from src.config.language_utils import LocalizedTemplateNotFoundError

class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, model: str = Settings.DEFAULT_MODEL, ollama_url: Optional[str] = None):
        """
        Initialize the Ollama client.
        
        Args:
            model: The model to use for requests
            ollama_url: URL for the Ollama API server
        """
        self.model = model
        # Use provided URL or environment variable or default
        self.base_url = ollama_url or os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
        self.api_url = f"{self.base_url}/api/generate"
        
    def _make_request(self, prompt: str, system: Optional[str] = None, 
                     max_attempts: int = 3, timeout: int = 300) -> Optional[str]:
        """
        Make a request to the Ollama API.
        
        Args:
            prompt: The prompt to send to the model
            system: Optional system message
            max_attempts: Maximum number of retry attempts
            timeout: Request timeout in seconds
            
        Returns:
            Model response text or None if the request failed
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            }
        }
        
        if system:
            payload["system"] = system
            
        attempt = 0
        while attempt < max_attempts:
            try:
                logging.debug(f"Sending request to Ollama API: {self.api_url}")
                response = requests.post(self.api_url, json=payload, timeout=timeout)
                
                if response.status_code == 200:
                    return response.json().get("response", "")
                else:
                    logging.error(f"Request failed with status code {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Request exception: {e}")
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {e}")
                
            attempt += 1
            if attempt < max_attempts:
                logging.info(f"Retrying request (attempt {attempt+1}/{max_attempts})...")
                time.sleep(2 ** attempt)  # Exponential backoff
                
        logging.error(f"Failed to get response from Ollama API after {max_attempts} attempts")
        return None
        
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
        return self._make_request(prompt, system, max_attempts)
    
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
            
        Raises:
            LocalizedTemplateNotFoundError: If required translation is not found
        """
        # Get the json format instruction from the translation resources
        json_validation_instruction = get_translation("json_format_instructions.json_format_instruction", language, None)
        if not json_validation_instruction:
            error_msg = f"No translation found for 'json_format_instructions.json_format_instruction' in language '{language}'"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
            
        # Update system prompt with the translated JSON instruction
        if system_prompt:
            system_prompt += f"\n{json_validation_instruction}"
        else:
            system_prompt = json_validation_instruction
        
        # Log the final prompt being sent
        logging.debug(f"LLM Prompt: {prompt}")
        if system_prompt:
            logging.debug(f"LLM System Prompt: {system_prompt}")
            
        raw_response = self._make_request(prompt, system_prompt, max_attempts)
        
        # Log the raw response received
        if raw_response:
            logging.debug(f"LLM Raw Response: {raw_response}")
        else:
            logging.debug("LLM Raw Response: None (Request failed)")
            
        if not raw_response:
            return None
            
        # Try to extract JSON from the response
        return self._extract_json(raw_response, max_attempts)
    
    def _extract_json(self, text: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """
        Try to extract valid JSON from the response text.
        
        Args:
            text: Text to parse for JSON
            max_attempts: Maximum number of attempts to fix and parse JSON
            
        Returns:
            Parsed JSON dict or None if parsing failed
        """
        # Log the first 200 characters of the response for debugging
        logging.debug(f"Attempting to extract JSON from: {text[:200]}...")
        
        # First try to directly parse the response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logging.debug("Direct JSON parsing failed, trying alternative methods")
        
        # Try to extract JSON from a code block
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logging.debug("Parsing JSON from code block failed")
        
        # Try to find JSON-like structure with {} brackets
        json_pattern = r'\{[\s\S]*\}'
        json_match = re.search(json_pattern, text)
        if json_match:
            try:
                extracted_json = json_match.group(0)
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                logging.debug(f"Parsing JSON with braces failed: {extracted_json[:100]}...")
                
                # Try more aggressive JSON fixing - common issues with Japanese text
                try:
                    # Fix missing quotes around keys
                    fixed_json = re.sub(r'([{,])\s*([^"{\s][^:{\s]*?)\s*:', r'\1"\2":', extracted_json)
                    
                    # Fix missing quotes around string values
                    fixed_json = re.sub(r':\s*([^"{}\[\],\s][^{}\[\],]*?)([,}])', r':"\1"\2', fixed_json)
                    
                    # Try to load the fixed JSON
                    return json.loads(fixed_json)
                except (json.JSONDecodeError, re.error) as e:
                    logging.debug(f"Advanced JSON fixing failed: {e}")
                
                # If regex fixing failed, try a more drastic approach for truncated JSON
                try:
                    # Try to balance braces by adding missing closing braces
                    open_braces = extracted_json.count('{')
                    close_braces = extracted_json.count('}')
                    if open_braces > close_braces:
                        fixed_json = extracted_json + "}" * (open_braces - close_braces)
                        return json.loads(fixed_json)
                except json.JSONDecodeError:
                    logging.debug("Brace balancing failed")
                
        # If all parsing attempts failed, log the error and return None
        logging.error(f"Failed to parse JSON from response: {text[:200]}...")
        return None 