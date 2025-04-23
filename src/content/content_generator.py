"""
Content generator for creating various file formats
"""

import datetime
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from src.content.file_manager import FileManager
from src.content.generators import (
    TextGenerator,
    DocxGenerator,
    PdfGenerator,
    XlsxGenerator,
    ImageGenerator
)
from src.foundation.llm_client import OllamaClient
from src.config.settings import Settings
from src.config.language_utils import get_translation


class ContentGenerator:
    """Generates content for various file formats"""
    
    # Maximum number of timeseries folders allowed at each level
    MAX_TIMESERIES_FOLDERS = 5
    
    def __init__(self, model: str = Settings.DEFAULT_MODEL, ollama_url: Optional[str] = None,
                date_start: Optional[datetime.datetime] = None,
                date_end: Optional[datetime.datetime] = None):
        """
        Initialize the content generator.
        
        Args:
            model: Model name to use for content generation
            ollama_url: URL for the Ollama API server
            date_start: Optional start date for date range hints (defaults to 30 days ago)
            date_end: Optional end date for date range hints (defaults to today)
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
        
        # Initialize date range parameters
        today = datetime.datetime.now()
        self.date_start = date_start or (today - datetime.timedelta(days=30))
        self.date_end = date_end or today
        self.date_range_str = None
        
    def _format_date_range(self, start_date: datetime.datetime, end_date: datetime.datetime, 
                          language: str) -> str:
        """
        Format date range as a string for use in prompts.
        
        Args:
            start_date: Start date
            end_date: End date
            language: Language code for translation
            
        Returns:
            Formatted date range string
            
        Raises:
            ValueError: If translation resource is not found
        """
        # Format dates individually
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
            
        # Use translation resource for date range format
        date_format_template = get_translation("date_range_format", language)
        
        # Check if translation was not found
        if date_format_template == "date_range_format":
            error_msg = f"No localized template found for '{language}' language (date_range_format)"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Use the translated template with formatted dates
        return date_format_template.format(start_date=start_date_str, end_date=end_date_str)
        
    def generate_file_content(self, file_path: str, file_type: str, description: str, 
                             industry: str, folder_path: str = "", language: str = "en", 
                             role: Optional[str] = None) -> bool:
        """
        Generate content for a specific file.
        
        Args:
            file_path: Full path to the file to create
            file_type: Type of the file (extension)
            description: Description of the file content
            industry: Industry context
            folder_path: Path of the folder containing the file
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if file was successfully created, False otherwise
        """
        try:
            # Get directory and filename from file_path
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # Handle empty directory case
            if not directory:
                logging.error(f"Empty directory path for file: {filename}")
                return False
                
            # Ensure the directory exists
            if not self.file_manager.ensure_directory(directory):
                logging.error(f"Failed to create directory for file: {filename}")
                return False
                
            # Get file extension from file_type if provided, or from filename
            if file_type and "." not in file_type:
                ext = file_type.lower()
            else:
                _, ext = os.path.splitext(filename)
                ext = ext.lstrip(".").lower()
                
            # Format date range if not already done
            if self.date_range_str is None and self.date_start and self.date_end:
                self.date_range_str = self._format_date_range(self.date_start, self.date_end, language)
                
            # Save file metadata separately
            file_metadata = {
                "filename": filename,
                "description": description,
                "industry": industry,
                "language": language,
                "role": role,
                "extension": ext,
                "folder_path": folder_path
            }
            
            # Add date range to metadata if available
            if self.date_range_str:
                file_metadata["date_range"] = self.date_range_str
            
            metadata_dir = os.path.join(directory, ".metadata")
            self.file_manager.ensure_directory(metadata_dir)
            metadata_filename = f"{self.file_manager.sanitize_path(filename)}.json"
            metadata_path = os.path.join(metadata_dir, metadata_filename)
            self.file_manager.write_json_file(metadata_path, file_metadata)
            
            # Generate the actual file content
            logging.info(f"Generating content for file {filename} (type: {ext})")
            
            # Use appropriate generator
            if ext in self.generators:
                return self.generators[ext].generate(
                    directory, filename, description, industry, language, role, 
                    date_range_str=self.date_range_str
                )
            elif ext in ["png", "jpg", "jpeg", "gif"]:
                return self.generators["image"].generate(
                    directory, filename, description, industry, language, role,
                    date_range_str=self.date_range_str
                )
            else:
                # Ignore unknown extensions
                logging.warning(f"Ignoring unknown file extension '{ext}': {filename}")
                return True
        except Exception as e:
            logging.error(f"Error generating file content for {file_path}: {e}")
            return False
        
    def generate_file(self, directory: str, filename: str, description: str,
                     industry: str, language: str, role: Optional[str] = None, 
                     purpose: Optional[str] = None) -> bool:
        """
        Generate a file with the appropriate content.
        
        Args:
            directory: Target directory for the file
            filename: Name of the file to create
            description: Description of the file content
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            purpose: Purpose of the folder (optional)
            
        Returns:
            True if file was successfully created, False otherwise
        """
        # Ensure the directory exists
        if not self.file_manager.ensure_directory(directory):
            return False
            
        # Get file extension to determine generator
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip(".").lower()
        
        # Handle timeseries folder purpose if specified
        if purpose == "timeseries":
            # Use date-based naming convention for files in timeseries folders
            filename = self._format_timeseries_filename(filename, ext)
        
        # Format date range if not already done
        if self.date_range_str is None and self.date_start and self.date_end:
            self.date_range_str = self._format_date_range(self.date_start, self.date_end, language)
            
        # Save file metadata separately
        file_metadata = {
            "filename": filename,
            "description": description,
            "industry": industry,
            "language": language,
            "role": role,
            "extension": ext,
            "purpose": purpose
        }
        
        # Add date range to metadata if available
        if self.date_range_str:
            file_metadata["date_range"] = self.date_range_str
        
        metadata_dir = os.path.join(directory, ".metadata")
        self.file_manager.ensure_directory(metadata_dir)
        metadata_filename = f"{self.file_manager.sanitize_path(filename)}.json"
        metadata_path = os.path.join(metadata_dir, metadata_filename)
        self.file_manager.write_json_file(metadata_path, file_metadata)
        
        # Use appropriate generator
        if ext in self.generators:
            return self.generators[ext].generate(
                directory, filename, description, industry, language, role,
                date_range_str=self.date_range_str
            )
        elif ext in ["png", "jpg"]:
            return self.generators["image"].generate(
                directory, filename, description, industry, language, role,
                date_range_str=self.date_range_str
            )
        else:
            # Ignore unknown extensions instead of creating text files
            logging.warning(f"Ignoring unknown file extension '{ext}' for file: {filename}")
            return True
        
    def _format_timeseries_filename(self, filename: str, ext: str) -> str:
        """
        Format a filename for timeseries folders using a date-based naming convention.
        
        Args:
            filename: Original filename
            ext: File extension
            
        Returns:
            Formatted filename with date prefix
        """
        today = datetime.datetime.now()
        date_prefix = today.strftime("%Y-%m-%d_")
        
        # Remove extension from filename
        name_without_ext = os.path.splitext(filename)[0]
        
        # Add date prefix if not already present
        if not name_without_ext.startswith(date_prefix):
            return f"{date_prefix}{filename}"
        
        return filename
    
    def is_timeseries_limit_reached(self, parent_dir: str) -> bool:
        """
        Check if the maximum number of timeseries folders has been reached.
        
        Args:
            parent_dir: Parent directory to check
            
        Returns:
            True if limit reached, False otherwise
        """
        # Count folders with timeseries purpose in metadata
        timeseries_count = 0
        
        try:
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path):
                    metadata_path = os.path.join(item_path, ".metadata.json")
                    if os.path.exists(metadata_path):
                        metadata = self.file_manager.read_json_file(metadata_path)
                        if metadata and metadata.get("purpose") == "timeseries":
                            timeseries_count += 1
            
            return timeseries_count >= self.MAX_TIMESERIES_FOLDERS
        except Exception as e:
            logging.error(f"Error checking timeseries folder limit: {e}")
            # Default to False on error
            return False
            
    def generate_timeseries_files(self, folder_path: str, folder_name: str, folder_description: str,
                                 industry: str, language: str, role: Optional[str] = None) -> List[str]:
        """
        Generate timeseries files for a folder.
        
        Args:
            folder_path: Path to the folder
            folder_name: Name of the folder
            folder_description: Description of the folder
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            List of created file paths
        """
        created_files = []
        try:
            # Generate time-based files
            today = datetime.datetime.now()
            
            # Format date range if not already done
            if self.date_range_str is None and self.date_start and self.date_end:
                self.date_range_str = self._format_date_range(self.date_start, self.date_end, language)
                
            # Create several files with different dates
            for i in range(3):  # Create 3 files by default
                # Use dates going backwards from today
                date = today - datetime.timedelta(days=i * 30)  # Monthly intervals
                date_str = date.strftime("%Y-%m-%d")
                
                # Create different file types
                file_types = ["xlsx", "pdf", "txt"]
                for file_type in file_types:
                    file_name = f"{date_str}_{folder_name}.{file_type}"
                    file_path = os.path.join(folder_path, file_name)
                    
                    # Skip if file already exists
                    if os.path.exists(file_path):
                        logging.info(f"File {file_path} already exists, skipping")
                        continue
                    
                    # Generate file content
                    description = f"Timeseries {file_type.upper()} file for {date_str} - {folder_description}"
                    if self.generate_file_content(file_path, file_type, description, industry, folder_path, language, role):
                        created_files.append(file_path)
                        
            return created_files
        except Exception as e:
            logging.exception(f"Error generating timeseries files: {e}")
            return created_files
            
    def update_date_range(self, date_start: Optional[datetime.datetime] = None, 
                        date_end: Optional[datetime.datetime] = None, 
                        language: str = "en") -> None:
        """
        Update the date range for content generation.
        
        Args:
            date_start: Start date for the date range
            date_end: End date for the date range
            language: Language code for translation
        """
        if date_start:
            self.date_start = date_start
        if date_end:
            self.date_end = date_end
            
        # Update the date range string
        if self.date_start and self.date_end:
            self.date_range_str = self._format_date_range(self.date_start, self.date_end, language) 