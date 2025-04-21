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

class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, model: str = "llama3", ollama_url: Optional[str] = None):
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
    
    def get_json_completion(self, prompt: str, system: Optional[str] = None, 
                           max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """
        Get a JSON formatted completion from the model.
        
        Args:
            prompt: The prompt to send to the model
            system: Optional system message
            max_attempts: Maximum number of retry attempts
            
        Returns:
            Parsed JSON response or None if parsing failed
        """
        system_prompt = system or ""
            
        if system_prompt:
            system_prompt += "\nYour response must be a valid JSON object. Do not include any explanations, markdown or text outside the JSON structure."
        else:
            system_prompt = "Your response must be a valid JSON object. Do not include any explanations, markdown or text outside the JSON structure."
        
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
        # First try to directly parse the response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # Try to extract JSON from a code block
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
                
        # Try to find JSON-like structure with {} brackets
        json_pattern = r'\{[\s\S]*\}'
        json_match = re.search(json_pattern, text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
                
        logging.error(f"Failed to parse JSON from response: {text[:100]}...")
        return None 