#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
import logging
import re
import traceback
from typing import Dict, List, Any, Tuple

# Import from local modules
from src.language_utils import get_normalized_language_key, load_prompt_templates

# Ollama server configuration
DEFAULT_OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "gemma3:4b"  # Default model to use

def extract_and_validate_json(json_string: str, expected_keys: List[str] = None) -> Dict:
    """Extract and validate JSON from a string, even if it's embedded in text"""
    if not json_string:
        logging.error("Empty JSON string received")
        return None
    
    # Try to find the JSON object between braces (simple approach)
    try:
        # Find the positions of the first { and the last }
        start_pos = json_string.find('{')
        end_pos = json_string.rfind('}') + 1
        
        if start_pos == -1 or end_pos == 0 or start_pos >= end_pos:
            logging.error(f"Could not locate valid JSON structure in: {json_string}")
            return None
        
        # Extract JSON substring
        json_substr = json_string[start_pos:end_pos]
        
        # Parse JSON
        json_data = json.loads(json_substr)
        
        # Debug output
        logging.info(f"Successfully extracted and parsed JSON")
        
        # Fix format if 'folders' is an array instead of an object
        if 'folders' in json_data and isinstance(json_data['folders'], list):
            logging.warning("Received 'folders' as an array instead of an object. Converting format...")
            folders_obj = {}
            for folder_item in json_data['folders']:
                if isinstance(folder_item, dict) and 'folder_name' in folder_item and 'description' in folder_item:
                    folder_name = folder_item['folder_name']
                    folder_desc = folder_item['description']
                    folders_obj[folder_name] = {'description': folder_desc}
                    
                    # If folder has subfolders, convert those too and rename key to 'folders'
                    if 'subfolders' in folder_item and isinstance(folder_item['subfolders'], list):
                        subfolders_obj = {}
                        for subfolder in folder_item['subfolders']:
                            if isinstance(subfolder, dict):
                                # Handle both 'name' and 'folder_name' cases
                                subfolder_name = subfolder.get('name') or subfolder.get('folder_name')
                                subfolder_desc = subfolder.get('description', '')
                                
                                if subfolder_name:
                                    subfolders_obj[subfolder_name] = {'description': subfolder_desc}
                                    
                                    # Handle third level subfolders if they exist
                                    if 'subfolders' in subfolder and isinstance(subfolder['subfolders'], list):
                                        sub_subfolders_obj = {}
                                        for sub_subfolder in subfolder['subfolders']:
                                            if isinstance(sub_subfolder, dict):
                                                sub_subfolder_name = sub_subfolder.get('name') or sub_subfolder.get('folder_name')
                                                sub_subfolder_desc = sub_subfolder.get('description', '')
                                                if sub_subfolder_name:
                                                    sub_subfolders_obj[sub_subfolder_name] = {'description': sub_subfolder_desc}
                                        
                                        if sub_subfolders_obj:
                                            subfolders_obj[subfolder_name]['folders'] = sub_subfolders_obj
                                    
                                    # Convert files array to proper format if it exists
                                    if 'files' in subfolder and isinstance(subfolder['files'], list):
                                        subfolders_obj[subfolder_name]['files'] = subfolder['files']
                        
                        if subfolders_obj:
                            folders_obj[folder_name]['folders'] = subfolders_obj
                    
                    # Add files if they exist in the folder
                    if 'files' in folder_item and isinstance(folder_item['files'], list):
                        folders_obj[folder_name]['files'] = folder_item['files']
            
            # Replace the array with the new object
            if folders_obj:
                json_data['folders'] = folders_obj
                logging.info(f"Successfully converted 'folders' array to object with {len(folders_obj)} keys")
            else:
                logging.error("Failed to convert 'folders' array to object format")
        
        # Fix format if 'subfolders' is used instead of 'folders' in nested levels
        def replace_subfolders_with_folders(obj):
            if isinstance(obj, dict):
                # Replace 'subfolders' with 'folders' at this level
                if 'subfolders' in obj:
                    if 'folders' not in obj:  # Don't overwrite if both keys exist
                        obj['folders'] = obj['subfolders']
                        del obj['subfolders']
                        logging.info("Replaced 'subfolders' key with 'folders'")
                
                # Recursively process all dictionary values
                for key, value in list(obj.items()):
                    if isinstance(value, dict):
                        replace_subfolders_with_folders(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                replace_subfolders_with_folders(item)
        
        # Apply the fix recursively
        replace_subfolders_with_folders(json_data)
        
        # Validate expected keys if provided
        if expected_keys:
            missing_keys = []
            for key in expected_keys:
                if key not in json_data:
                    missing_keys.append(key)
            
            if missing_keys:
                logging.warning(f"Generated JSON is missing expected keys: {missing_keys}")
                logging.warning(f"Available keys: {list(json_data.keys())}")
                # Return the parsed JSON without reporting error
                return json_data
            else:
                logging.info(f"Generated JSON contains all expected keys: {expected_keys}")
        
        return json_data
    
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        logging.error(f"JSON substring: {json_substr}")
        return None
    
    except Exception as e:
        logging.error(f"Error processing JSON: {e}")
        return None

def extract_json_from_llm_response(text: str) -> str:
    """
    Extract JSON content from LLM response text.
    This handles various formats including code blocks and improper JSON.
    It aggressively strips unwanted text/remarks that LLMs often add before and after JSON.
    
    Args:
        text: The raw text from the LLM response
        
    Returns:
        Extracted JSON string or empty string if no JSON found
    """
    if not text:
        return ""
        
    # Remove leading and trailing whitespace from the entire text
    text = text.strip()
    
    # First, try to find complete JSON enclosed in braces
    # This is the most reliable method if available
    json_pattern = r'(\{[\s\S]*\})'
    json_matches = re.findall(json_pattern, text)
    
    if json_matches:
        # Find the largest JSON object (most likely the complete one)
        candidate = max(json_matches, key=len)
        try:
            # Validate it's proper JSON
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            # If it's not valid JSON, we'll try other methods
            pass
    
    # Handle common case where there are code block markers
    if "```" in text:
        # Try to extract content between code block markers with specific language tags
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(code_block_pattern, text)
        
        if matches:
            # Use the largest code block (most likely to be the complete JSON)
            extracted = max(matches, key=len).strip()
            # Try both the extracted content as-is and finding JSON object within it
            try:
                json.loads(extracted)
                return extracted
            except json.JSONDecodeError:
                # If extracted content isn't valid JSON, look for JSON objects within it
                inner_matches = re.findall(r'(\{[\s\S]*\})', extracted)
                if inner_matches:
                    candidate = max(inner_matches, key=len)
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        pass
    
    # Last resort: look for anything that might be JSON (aggressive matching)
    # Look for the first opening brace and last closing brace
    if '{' in text and '}' in text:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace < last_brace:
            candidate = text[first_brace:last_brace+1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
    
    # If all else fails, try to capture any JSON-like structure
    json_pattern = r'(\{[\s\S]*?\})'
    json_matches = re.findall(json_pattern, text)
    
    if json_matches:
        # Return the largest match as it's likely the full JSON object
        for candidate in sorted(json_matches, key=len, reverse=True):
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue
    
    # No valid JSON found
    return ""

def fix_json_with_llm(broken_json: str, error_message: str, model: str = None, ollama_url: str = None, structure_hint: str = "", language: str = "en-US") -> str:
    """
    Use LLM to fix broken JSON.
    
    Args:
        broken_json: The broken JSON string to fix
        error_message: The error message from the JSON parser
        model: LLM model to use
        ollama_url: Ollama API URL
        structure_hint: Hint about the expected JSON structure
        language: Language code for templates
        
    Returns:
        Fixed JSON string or empty string if fixing failed
    """
    try:
        # Load the language-specific template
        language_key = get_normalized_language_key(language)
        templates = load_prompt_templates(language_key)
        
        # Get the JSON fix prompt template
        fix_json_template = templates.get("json_fix_prompts", {}).get("fix_json", "")
        
        # If template is not found, use a default one
        if not fix_json_template:
            logging.warning(f"JSON fix prompt template not found for language {language_key}. Using default.")
            fix_json_template = "Please fix this invalid JSON and return ONLY the corrected JSON without explanation:\n{failed_response}\n\nError: {error_message}\n\n{structure_hint}"
        
        # Prepare prompt for fixing JSON
        prompt = fix_json_template.replace("{failed_response}", broken_json)
        
        # Add structure hint if provided
        if structure_hint:
            prompt = prompt.replace("{structure_hint}", f"Expected structure: {structure_hint}")
        else:
            prompt = prompt.replace("{structure_hint}", "")
        
        # Add error message if the template has a placeholder for it
        if "{error_message}" in prompt:
            prompt = prompt.replace("{error_message}", error_message)
        elif "error" not in prompt.lower():
            prompt += f"\n\nThe JSON parser error was: `{error_message}`"
        
        # Log the prompt
        logging.info(f"========= JSON FIX PROMPT START =========")
        logging.info(prompt)
        logging.info(f"========== JSON FIX PROMPT END ==========")
        
        # Get model and URL
        model_to_use = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        api_url = ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        
        # Call Ollama API
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "temperature": 0.1,  # Lower temperature for more deterministic response
            "stream": False
        }
        
        logging.info("Calling LLM to fix broken JSON")
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 200:
            response_json = response.json()
            fixed_text = response_json.get("response", "")
            
            # Log the response
            logging.info(f"========= JSON FIX RESPONSE START =========")
            logging.info(fixed_text)
            logging.info(f"========== JSON FIX RESPONSE END ==========")
            
            # Extract JSON from the response
            extracted_json = extract_json_from_llm_response(fixed_text)
            if extracted_json:
                try:
                    # Validate that it's proper JSON
                    json.loads(extracted_json)
                    logging.info("Successfully fixed and validated JSON")
                    return extracted_json
                except json.JSONDecodeError as e:
                    logging.warning(f"LLM returned invalid JSON: {e}")
            else:
                # If no JSON found but the response itself might be JSON
                try:
                    json.loads(fixed_text)
                    logging.info("Raw response is valid JSON")
                    return fixed_text
                except json.JSONDecodeError:
                    # If the response itself wasn't JSON, try adding braces
                    if not fixed_text.strip().startswith("{"):
                        try:
                            with_braces = "{" + fixed_text.strip() + "}"
                            json.loads(with_braces)
                            logging.info("Adding braces fixed the JSON")
                            return with_braces
                        except json.JSONDecodeError:
                            logging.warning("Could not fix JSON by adding braces")
            
            logging.warning("LLM couldn't fix the JSON properly")
        else:
            logging.error(f"Error calling LLM to fix JSON: {response.status_code}")
        
        return ""
    except Exception as e:
        logging.error(f"Error in fix_json_with_llm: {e}")
        return ""

def call_ollama(prompt: str, model: str = None, ollama_url: str = None) -> str:
    """Call Ollama API with the given prompt"""
    try:
        # Get Ollama URL from parameter, environment variable or use default
        ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        
        # Get model from parameter, environment or use default
        model_to_use = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        temperature = float(os.environ.get("OLLAMA_TEMPERATURE", "0.7"))
        
        logging.info(f"Using Ollama URL: {ollama_url}")
        logging.info(f"Using Ollama model: {model_to_use} (temperature: {temperature})")
        
        # Log the prompt
        logging.info(f"========= OLLAMA PROMPT START =========")
        logging.info(prompt)
        logging.info(f"========== OLLAMA PROMPT END ==========")
        
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        response = requests.post(ollama_url, json=payload)
        if response.status_code == 200:
            response_json = response.json()
            response_text = response_json.get("response", "")
            
            # Log the response
            logging.info(f"========= OLLAMA RESPONSE START =========")
            logging.info(response_text)
            logging.info(f"========== OLLAMA RESPONSE END ==========")
            
            return response_text
        else:
            error_msg = f"Ollama API returned status code {response.status_code}: {response.text}"
            logging.error(error_msg)
            # Terminate abnormally
            if "model" in response.text and "not found" in response.text:
                logging.critical(f"Model '{model_to_use}' not found. Terminating program.")
                sys.exit(1)
            elif response.status_code == 404:
                logging.critical("Ollama API not found. Please ensure Ollama is running.")
                sys.exit(1)
            else:
                logging.critical("An error occurred with the Ollama API. Terminating program.")
                sys.exit(1)
    except Exception as e:
        logging.error(f"Error calling Ollama: {e}")
        logging.critical("Ollama connection error. Terminating program.")
        sys.exit(1)

def call_ollama_json(prompt: str, model: str = None, ollama_url: str = None, structure_hint: str = "", expected_keys: List[str] = None, max_attempts: int = 5, 
                  temp_reduction: float = 0.7, min_temperature: float = 0.1, 
                  language: str = "en-US") -> Dict[str, Any]:
    """
    Connect to Ollama API and get JSON response.
    This is the standard function for handling all LLM-generated JSON in the application.
    
    Args:
        prompt: The prompt to send to the LLM
        model: The LLM model to use
        ollama_url: The URL of the Ollama API
        structure_hint: Hint about the expected JSON structure
        expected_keys: List of expected keys in the JSON
        max_attempts: Maximum number of attempts to parse the JSON
        temp_reduction: Factor to reduce temperature by on retry (0-1)
        min_temperature: Minimum temperature value for retries
        language: Language code for the response (default: en-US)
        
    Returns:
        Dict containing the parsed JSON response
    """
    try:
        # Get Ollama URL from parameter, environment variable or use default
        ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        
        # Get model and temperature from environment variables
        model_to_use = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        temperature = float(os.environ.get("OLLAMA_TEMPERATURE", "0.7"))
        
        logging.info(f"Using Ollama URL for JSON: {ollama_url}")
        logging.info(f"Using Ollama model for JSON: {model_to_use} (temperature: {temperature})")
        
        # Load language templates for messages
        templates = load_prompt_templates(language)
        json_format_instructions = templates.get("json_format_instructions", {})
        
        # Initialize expected_keys as empty list if None
        if expected_keys is None:
            expected_keys = []
            
        # Extract expected keys from structure_hint
        if structure_hint:
            # Look for keys mentioned in the structure hint
            key_pattern = r'keys\s+like\s+["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])*'
            matches = re.findall(key_pattern, structure_hint)
            if matches:
                # Extract all keys from the matches
                for match in matches:
                    for group in match:
                        if group and group not in expected_keys:
                            expected_keys.append(group)
            
            # If no keys found with the pattern, try to find quoted words
            if not expected_keys:
                quoted_keys = re.findall(r'["\']([^"\']+)["\']', structure_hint)
                expected_keys = [key for key in quoted_keys if len(key) > 2]  # Only use keys with length > 2 to avoid noise
        
        logging.info(f"Expected keys from structure hint: {expected_keys}")
        
        # Determine language for JSON format instructions
        language_key = get_normalized_language_key(language)
        
        # Get JSON format instruction from language templates
        json_format_instruction = ""
        if "JSON" not in prompt and "json" not in prompt:
            # Only add if not already in prompt
            format_instruction = json_format_instructions.get("json_format_instruction", 
                "Please format your response as a valid JSON object with proper braces and quotes.")
            json_format_instruction = f"\n\n{format_instruction}"
        
        # Enhance prompt to explicitly request JSON format with clear structure expectations
        base_prompt = prompt
        if json_format_instruction:
            base_prompt += json_format_instruction
            
        # Add structure hint if provided, but ensure it's in the same language
        if structure_hint:
            base_prompt += f"\n\n{structure_hint}"
        
        # Keep track of error messages to avoid duplication
        current_error_msg = ""
        
        # Keep track of our attempts
        for attempt in range(1, max_attempts + 1):
            logging.info(f"JSON generation attempt {attempt}/{max_attempts}")
            
            # Construct prompt for this attempt (base + current error if any)
            json_prompt = base_prompt
            if current_error_msg:
                json_prompt += f"\n\n{current_error_msg}"
            
            # Log the prompt for this attempt
            logging.info(f"========= JSON PROMPT (Attempt {attempt}) START =========")
            logging.info(json_prompt)
            logging.info(f"========== JSON PROMPT (Attempt {attempt}) END ==========")
            
            try:
                # Call Ollama API
                payload = {
                    "model": model_to_use,
                    "prompt": json_prompt,
                    "temperature": temperature,
                    "stream": False
                }
                
                response = requests.post(ollama_url, json=payload)
                
                if response.status_code != 200:
                    error_msg = f"Ollama API returned status code {response.status_code}: {response.text}"
                    logging.error(error_msg)
                    
                    if "model" in response.text and "not found" in response.text:
                        logging.critical(f"Model '{model_to_use}' not found. Terminating program.")
                        sys.exit(1)
                    elif response.status_code == 404:
                        logging.critical("Ollama API not found. Please ensure Ollama is running.")
                        sys.exit(1)
                    else:
                        if attempt < max_attempts:
                            logging.warning(f"API error on attempt {attempt}, retrying...")
                            continue
                        else:
                            logging.critical("All attempts to call Ollama API failed. Terminating program.")
                            sys.exit(1)

                # Get response text
                response_json = response.json()
                response_text = response_json.get("response", "")
                
                # Log full response for debugging (change from debug to info level)
                logging.info(f"========= JSON RESPONSE (Attempt {attempt}) START =========")
                logging.info(response_text)
                logging.info(f"========== JSON RESPONSE (Attempt {attempt}) END ==========")
                
                # Use the new extraction and validation function
                parsed_json = extract_and_validate_json(response_text, expected_keys)
                
                if parsed_json:
                    # Check if structure requirements are met
                    if expected_keys:
                        missing_keys = [key for key in expected_keys if key not in parsed_json]
                        if missing_keys:
                            # For structure mismatch, don't try to fix - retry with clearer prompt
                            if attempt < max_attempts:
                                logging.info("Structure mismatch detected. Retrying generation with clarified prompt...")
                                # Add clearer structure requirements using template from parameters
                                missing_keys_str = ', '.join(missing_keys)
                                
                                # Get structure error message from language templates
                                error_format = json_format_instructions.get("structure_error_format", 
                                    "IMPORTANT: JSON must include the following keys: {keys}. All folder names must be in English.")
                                current_error_msg = error_format.format(keys=missing_keys_str)
                                
                                # Decrease temperature for more precise output using parameters
                                temperature = max(min_temperature, temperature * temp_reduction)
                                continue
                            else:
                                logging.critical(f"Failed to generate JSON with required structure after {max_attempts} attempts")
                                return None
                    
                    # If we have a valid JSON with proper structure, return it
                    return parsed_json
                
                # If extraction failed, continue with the next attempt
                if attempt < max_attempts:
                    logging.warning(f"JSON parsing failed in attempt {attempt}. Retrying...")
                    # Add more explicit instructions for next attempt from language templates
                    current_error_msg = json_format_instructions.get("parsing_error_message", 
                        "IMPORTANT: There was an error parsing your previous response. Please provide a valid JSON object with correct braces.")
                    
                    # Decrease temperature for more precise output
                    temperature = max(min_temperature, temperature * temp_reduction)
                else:
                    logging.critical(f"All {max_attempts} attempts to generate and parse JSON failed.")
                    logging.critical("Response text: " + response_text[:500] + "..." if len(response_text) > 500 else response_text)
                    return None
                    
            except Exception as e:
                if attempt < max_attempts:
                    logging.warning(f"Error in JSON processing attempt {attempt}: {e}. Retrying...")
                else:
                    logging.error(f"Error calling Ollama for JSON: {e}")
                    logging.critical("Ollama JSON connection error. Terminating program.")
                    sys.exit(1)
    
        # This should not be reached due to returns or exits above
        logging.critical("Unexpected error in JSON generation")
        sys.exit(1)
            
    except Exception as e:
        logging.error(f"Fatal error in call_ollama_json: {e}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1) 