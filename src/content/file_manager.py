"""
File manager to handle file operations
"""

import logging
import os
from pathlib import Path
import re
import json
from typing import Optional, Dict, Any

class FileManager:
    """Handles file operations for the project"""
    
    @staticmethod
    def sanitize_path(path_str: str) -> str:
        """
        Sanitize a path string to ensure it's valid for file system.
        
        Args:
            path_str: Path string to sanitize
            
        Returns:
            Sanitized path string
        """
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"|?*]', '_', path_str)
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        # Remove trailing periods and spaces
        sanitized = sanitized.rstrip('. ')
        # Replace multiple spaces with a single one
        sanitized = re.sub(r'\s+', ' ', sanitized)
        return sanitized
    
    @staticmethod
    def ensure_directory(directory_path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to the directory
            
        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"Failed to create directory {directory_path}: {e}")
            return False
    
    @staticmethod
    def write_text_file(file_path: str, content: str) -> bool:
        """
        Write content to a text file.
        
        Args:
            file_path: Path to the file
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logging.error(f"Failed to write file {file_path}: {e}")
            return False
    
    @staticmethod
    def write_json_file(file_path: str, data: Dict[str, Any]) -> bool:
        """
        Write data to a JSON file.
        
        Args:
            file_path: Path to the file
            data: Data to write as JSON
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to write JSON file {file_path}: {e}")
            return False
            
    @staticmethod
    def read_text_file(file_path: str) -> Optional[str]:
        """
        Read content from a text file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string if successful, None otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")
            return None
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file exists, False otherwise
        """
        return os.path.isfile(file_path)
            
    @staticmethod
    def create_path(base_dir: str, *parts) -> str:
        """
        Create a file path by joining base directory and parts.
        
        Args:
            base_dir: Base directory
            *parts: Path parts to join
            
        Returns:
            Joined path
        """
        # Sanitize each part
        sanitized_parts = [FileManager.sanitize_path(part) for part in parts if part]
        # Join with base directory
        return os.path.join(base_dir, *sanitized_parts)
    
    @staticmethod
    def read_json_file(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read data from a JSON file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Data from JSON file if successful, None otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to read JSON file {file_path}: {e}")
            return None 