"""
Folder structure generator
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
import random

from ..config.language_utils import get_translation
from ..content.content_generator import ContentGenerator
from ..content.file_manager import FileManager
from ..foundation.llm_client import OllamaClient
from ..statistics.statistics_tracker import StatisticsTracker
from ..config.settings import Settings
from .json_templates import JsonTemplates


# Custom exception for short mode limit
class ShortModeLimitReached(Exception):
    pass

# Custom exception for missing localized template
class LocalizedTemplateNotFoundError(Exception):
    """Raised when a localized template is not found for the selected language."""
    pass

class FolderGenerator:
    """
    Generates folder structures and instructs content creation
    
    This class handles the generation of folder structures and files based on industry,
    language, and role specifications. It can create a complete hierarchy with:
    - Level 1 folders (root level)
    - Level 2 folders (within level 1)
    - Level 3 folders (within level 2)
    - Files with appropriate content
    
    Date range functionality:
    - Default date range is the last 30 days
    - Date range is used to generate hints for time-based folder and file names
    - Can be customized by providing start and end dates
    """
    
    # Item type constants
    ITEM_TYPE_FOLDER = "folder"
    ITEM_TYPE_FILE = "file"
    ITEM_TYPE_IMAGE = "image"  # For future use
    
    # Short mode limits
    SHORT_MODE_LIMITS = {
        ITEM_TYPE_FOLDER: 10,  # Limit for folders
        ITEM_TYPE_FILE: 10,    # Limit for files
        ITEM_TYPE_IMAGE: 0     # No limit for images by default
    }

    def __init__(self, model: str = Settings.DEFAULT_MODEL, ollama_url: Optional[str] = None, 
                 settings: Optional[Settings] = None, date_start: Optional[datetime] = None, 
                 date_end: Optional[datetime] = None):
        """
        Initialize the folder generator.
        
        Args:
            model: Model name to use for generation
            ollama_url: URL for the Ollama API server
            settings: Application settings
            date_start: Optional start date for date range hints (defaults to 30 days ago)
            date_end: Optional end date for date range hints (defaults to today)
            
        Raises:
            LocalizedTemplateNotFoundError: If required translations are missing
            ValueError: If language is not set in settings
        """
        self.llm_client = OllamaClient(model, ollama_url)
        self.file_manager = FileManager()
        
        # Initialize date range parameters
        today = datetime.now()
        self.date_start = date_start or (today - timedelta(days=30))
        self.date_end = date_end or today
        
        # Initialize content generator with date range
        self.content_generator = ContentGenerator(
            model, 
            ollama_url,
            date_start=self.date_start,
            date_end=self.date_end
        )
        
        self._item_counts = {item_type: 0 for item_type in self.SHORT_MODE_LIMITS.keys()}  # Initialize counters for all item types
        self._short_mode_enabled = False # Flag to store if short mode is active for the current run
        self.statistics_tracker = StatisticsTracker() # Initialize statistics tracker
        self.settings = settings or Settings() # Store settings or create default instance
        
        # Validate language is set
        language = getattr(self.settings, 'language', None)
        if not language:
            error_msg = "Language is not set in settings"
            logging.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate translation for date_range_format exists
        date_format_template = get_translation("date_range_format", language)
        if date_format_template == "date_range_format":
            error_msg = f"No localized template found for '{language}' language (date_range_format)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
            
        # Format the date range string
        self.date_range_str = self._format_date_range(self.date_start, self.date_end)
        
    def _format_date_range(self, start_date: datetime, end_date: datetime) -> str:
        """
        Format date range as a string for use in prompts.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Formatted date range string
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the date range format
            ValueError: If language is not set in settings
        """
        # Get language from settings without a default
        language = getattr(self.settings, 'language', None)
        
        # Raise exception if language is not set
        if not language:
            error_msg = "Language is not set in settings"
            logging.error(error_msg)
            raise ValueError(error_msg)
            
        # Format dates individually to avoid locale-specific issues
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
            
        # Use translation resource for date range format
        date_format_template = get_translation("date_range_format", language)
        
        # Use the translated template with formatted dates
        return date_format_template.format(start_date=start_date_str, end_date=end_date_str)
        
    # --- Public Methods (expected by sharinbai.py) with Short Mode --- 

    def generate_all(self, output_path: str, industry: str, language: str, 
                     role: Optional[str] = None, short_mode: bool = False,
                     date_start: Optional[datetime] = None, 
                     date_end: Optional[datetime] = None) -> bool:
        """Generate complete folder structure with files."""
        # Update date range if provided
        if date_start or date_end:
            self.date_start = date_start or self.date_start
            self.date_end = date_end or self.date_end
            self.date_range_str = self._format_date_range(self.date_start, self.date_end)
            
            # Update ContentGenerator's date range
            self.content_generator.update_date_range(
                self.date_start, 
                self.date_end,
                language
            )
            
        self._reset_short_mode(short_mode, mode="all")
        try:
            base_dir = Path(output_path)
            
            # Create logs and target directories
            logs_dir = Path(self.settings.log_path)
            target_dir = base_dir 
            
            if not self.file_manager.ensure_directory(str(logs_dir)):
                return False
                
            if not self.file_manager.ensure_directory(str(target_dir)):
                return False
            
            self.statistics_tracker.start_tracking_item("level1_structure_generation")
            level1_structure = self._generate_level1_folders(industry, language, role)
            self.statistics_tracker.end_tracking_item()
            
            if not level1_structure or "folders" not in level1_structure:
                logging.error("Failed to generate valid level 1 folder structure")
                return False
                
            result = self._process_folder_structure(level1_structure, target_dir, industry, language, role)
            
            # Print statistics at the end
            self.statistics_tracker.print_statistics(language)
            
            return result
        except ShortModeLimitReached:
            logging.info("Folder generation stopped due to short mode limit.")
            
            # Print statistics even when stopped early
            self.statistics_tracker.print_statistics(language)
            
            return True
        except LocalizedTemplateNotFoundError as e:
            logging.error(f"Language resource error: {e}")
            return False
        except Exception as e:
            logging.exception(f"Error during full generation: {e}")
            return False

    def generate_structure_only(self, output_path: str, industry: str, language: str, 
                                role: Optional[str] = None, short_mode: bool = False,
                                date_start: Optional[datetime] = None, 
                                date_end: Optional[datetime] = None) -> bool:
        """Generate folder structure only without files."""
        # Update date range if provided
        if date_start or date_end:
            self.date_start = date_start or self.date_start
            self.date_end = date_end or self.date_end
            self.date_range_str = self._format_date_range(self.date_start, self.date_end)
            
            # Update ContentGenerator's date range
            self.content_generator.update_date_range(
                self.date_start, 
                self.date_end,
                language
            )
            
        self._reset_short_mode(short_mode, mode="structure")
        try:
            base_dir = Path(output_path)
            
            # Create target directory directly under the base path
            target_dir = base_dir
            
            if not self.file_manager.ensure_directory(str(target_dir)):
                return False
                
            self.statistics_tracker.start_tracking_item("level1_structure_generation")
            level1_structure = self._generate_level1_folders(industry, language, role)
            self.statistics_tracker.end_tracking_item()
            
            if not level1_structure or "folders" not in level1_structure:
                logging.error("Failed to generate valid level 1 folder structure")
                return False
                
            result = self._process_structure_only(level1_structure, target_dir, industry, language, role)
            
            # Print statistics at the end
            self.statistics_tracker.print_statistics(language)
            
            return result
        except ShortModeLimitReached:
            logging.info("Folder generation stopped due to short mode limit.")
            
            # Print statistics even when stopped early
            self.statistics_tracker.print_statistics(language)
            
            return True
        except LocalizedTemplateNotFoundError as e:
            logging.error(f"Language resource error: {e}")
            return False
        except Exception as e:
            logging.exception(f"Error during structure only generation: {e}")
            return False

    def generate_files_only(self, output_path: str, industry: str, language: str,
                            role: Optional[str] = None, short_mode: bool = False,
                            date_start: Optional[datetime] = None, 
                            date_end: Optional[datetime] = None) -> bool:
        """Generate or update files only without modifying folder structure."""
        # Update date range if provided
        if date_start or date_end:
            self.date_start = date_start or self.date_start
            self.date_end = date_end or self.date_end
            self.date_range_str = self._format_date_range(self.date_start, self.date_end)
            
            # Update ContentGenerator's date range
            self.content_generator.update_date_range(
                self.date_start, 
                self.date_end,
                language
            )
            
        self._reset_short_mode(short_mode, mode="file")
        try:
            base_dir = Path(output_path)
            target_dir = base_dir
            
            if not target_dir.exists():
                 logging.error(f"Target directory {target_dir} does not exist. Run 'all' or 'structure' first.")
                 return False
                 
            # Industry/language needed for regeneration prompts even if metadata has them
            result = self._regenerate_files(target_dir, industry, language, role)
            
            # Print statistics at the end
            self.statistics_tracker.print_statistics(language)
            
            return result
        except ShortModeLimitReached:
            logging.info("File generation stopped due to short mode limit.")
            
            # Print statistics even when stopped early
            self.statistics_tracker.print_statistics(language)
            
            return True
        except LocalizedTemplateNotFoundError as e:
            logging.error(f"Language resource error: {e}")
            return False
        except Exception as e:
            logging.exception(f"Error during file only generation: {e}")
            return False
            
    def generate_files_in_folders(self, output_path: str, industry: str, language: str,
                               role: Optional[str] = None, short_mode: bool = False,
                               target_folders: List[Path] = None, max_files: int = 10,
                               date_start: Optional[datetime] = None, 
                               date_end: Optional[datetime] = None) -> bool:
        """Generate files in selected random folders without modifying folder structure."""
        # Update date range if provided
        if date_start or date_end:
            self.date_start = date_start or self.date_start
            self.date_end = date_end or self.date_end
            self.date_range_str = self._format_date_range(self.date_start, self.date_end)
            
            # Update ContentGenerator's date range
            self.content_generator.update_date_range(
                self.date_start, 
                self.date_end,
                language
            )
            
        self._reset_short_mode(short_mode, mode="file")
        try:
            base_dir = Path(output_path)
            target_dir = base_dir
            
            if not target_dir.exists():
                logging.error(f"Target directory {target_dir} does not exist. Run 'all' or 'structure' first.")
                return False
                
            if not target_folders or len(target_folders) == 0:
                logging.error("No target folders provided for file generation.")
                return False
            
            # Track success across all folders
            overall_success = True
            files_generated = 0
            target_folders = list(target_folders)  # Convert to list if it's not already
            
            # Shuffle the folders to ensure randomness
            random.shuffle(target_folders)
            
            # Keep track of files to generate per folder to distribute evenly
            files_per_folder = max(1, max_files // len(target_folders))
            remaining_files = max_files
            
            logging.info(f"Planning to generate approximately {files_per_folder} files per folder in {len(target_folders)} folders")
            
            # Process each target folder
            for folder_path in target_folders:
                if remaining_files <= 0:
                    logging.info(f"Reached target of {max_files} files generated, stopping.")
                    break
                    
                if not folder_path.exists():
                    logging.warning(f"Folder {folder_path} does not exist, skipping.")
                    continue
                
                # Read folder metadata for context
                folder_metadata = None
                folder_description = ""
                metadata_path = folder_path / ".metadata.json"
                
                if metadata_path.exists():
                    folder_metadata = self.file_manager.read_json_file(str(metadata_path))
                    if folder_metadata:
                        folder_description = folder_metadata.get("description", "")
                
                # Get folder path for context
                try:
                    rel_path = folder_path.relative_to(target_dir)
                    folder_path_str = str(rel_path)
                except ValueError:
                    folder_path_str = folder_path.name
                
                logging.info(f"Generating files in folder: {folder_path_str}")
                
                # Determine how many files to generate in this folder
                files_to_generate = min(files_per_folder, remaining_files)
                
                # Ask LLM to update folder metadata with file suggestions
                folder_metadata_updated = self._update_folder_metadata_with_llm(
                    folder_path_str, 
                    folder_description, 
                    folder_metadata, 
                    industry, 
                    files_to_generate
                )
                
                # Extract file definitions from updated metadata
                files_to_create = []
                
                if folder_metadata_updated and "files" in folder_metadata_updated:
                    files_part = folder_metadata_updated["files"]
                    
                    # Handle both list and dict format for files
                    if isinstance(files_part, list):
                        files_to_create = files_part
                    elif isinstance(files_part, dict):
                        for file_name, file_data in files_part.items():
                            if isinstance(file_data, dict):
                                file_data["name"] = file_name
                                files_to_create.append(file_data)
                
                # If we didn't get any files from the LLM, generate them individually
                if not files_to_create:
                    logging.warning(f"No files returned from LLM for {folder_path_str}, generating individually")
                    # Generate files one by one
                    for _ in range(files_to_generate):
                        file_data = self._generate_random_file_data(folder_path_str, folder_description, industry)
                        if file_data and "name" in file_data:
                            files_to_create.append(file_data)
                            
                # Merge updated metadata with existing metadata
                if folder_metadata_updated and folder_metadata:
                    # Update description if it changed significantly
                    if "description" in folder_metadata_updated and folder_metadata_updated["description"] != folder_description:
                        folder_metadata["description"] = folder_metadata_updated["description"]
                        
                    # Update purpose if provided
                    if "purpose" in folder_metadata_updated:
                        folder_metadata["purpose"] = folder_metadata_updated["purpose"]
                    
                    # Initialize files dictionary if it doesn't exist
                    if "files" not in folder_metadata:
                        folder_metadata["files"] = {}
                    
                    # Write updated metadata back to disk
                    self.file_manager.write_json_file(str(metadata_path), folder_metadata)
                    logging.info(f"Updated folder metadata for {folder_path_str}")
                elif folder_metadata_updated:
                    # Write the new metadata to disk
                    self.file_manager.write_json_file(str(metadata_path), folder_metadata_updated)
                    logging.info(f"Created new folder metadata for {folder_path_str}")
                    folder_metadata = folder_metadata_updated
                
                # Generate files from the prepared list
                file_count = 0
                
                # Process each file in the list
                for file_data in files_to_create:
                    if remaining_files <= 0:
                        break
                        
                    if not file_data or "name" not in file_data:
                        continue
                    
                    try:
                        file_name = file_data["name"]
                        file_path = folder_path / self.file_manager.sanitize_path(file_name)
                        
                        # Skip if file already exists
                        if file_path.exists():
                            logging.info(f"File {file_name} already exists in {folder_path_str}, skipping")
                            continue
                        
                        # Get file type from extension or explicit type field
                        file_type = file_data.get("type", "")
                        if not file_type and "." in file_name:
                            file_type = file_name.split(".")[-1]
                        
                        # Generate file content
                        success = self.content_generator.generate_file_content(
                            str(file_path),
                            file_type,
                            file_data.get("description", ""),
                            industry,
                            folder_path_str,
                            language,
                            role
                        )
                        
                        if success:
                            files_generated += 1
                            self.statistics_tracker.add_file(str(file_path))
                            logging.info(f"Created file: {folder_path_str}/{file_name}")
                            file_count += 1
                            remaining_files -= 1
                            
                            # Update metadata with new file
                            if folder_metadata and isinstance(folder_metadata, dict):
                                if "files" not in folder_metadata:
                                    folder_metadata["files"] = {}
                                
                                # Add generated file to metadata
                                folder_metadata["files"][file_name] = {k: v for k, v in file_data.items() if k != "name"}
                                
                                # Write updated metadata
                                self.file_manager.write_json_file(str(metadata_path), folder_metadata)
                        else:
                            logging.error(f"Failed to generate file {file_name} in {folder_path_str}")
                            overall_success = False
                    except Exception as e:
                        logging.error(f"Error generating file in {folder_path_str}: {e}")
                        overall_success = False
                
                logging.info(f"Generated {file_count} files in folder {folder_path_str}")
            
            logging.info(f"Total files generated: {files_generated} out of requested {max_files}")
            
            # Print statistics at the end
            self.statistics_tracker.print_statistics(language)
            
            return overall_success
        except ShortModeLimitReached:
            logging.info("File generation stopped due to short mode limit.")
            
            # Print statistics even when stopped early
            self.statistics_tracker.print_statistics(language)
            
            return True
        except LocalizedTemplateNotFoundError as e:
            logging.error(f"Language resource error: {e}")
            return False
        except Exception as e:
            logging.exception(f"Error during file generation in folders: {e}")
            return False
    
    def _generate_random_file_data(self, folder_path: str, folder_description: str, industry: str) -> Dict[str, Any]:
        """Generate random file data based on folder context."""
        # Use LLM to generate file metadata based on folder context
        try:
            # Get localized prompt template for generating a single file metadata
            prompt_template = get_translation("folder_structure_prompt.single_file_metadata", self.settings.language)
            if not prompt_template:
                # No fallback - fail fast
                logging.error(f"Missing translation for single_file_metadata in language {self.settings.language}")
                raise LocalizedTemplateNotFoundError(f"No translation found for single_file_metadata in {self.settings.language}")
            
            # Get JSON template and localized descriptions
            json_template = JsonTemplates.get_template("single_file_metadata")
            if not json_template:
                logging.error("Missing JSON template for single_file_metadata")
                raise ValueError("JSON template not found for single_file_metadata")
            
            # Get localized description template
            file_description_template = get_translation(
                "description_templates.file_description", 
                self.settings.language
            )
            
            # Apply localized descriptions to the template
            json_template = json_template.format(
                file_description=file_description_template
            )
            
            # Replace placeholders in the template
            date_range = self.date_range_str or f"{self.date_start.strftime('%Y-%m-%d')} to {self.date_end.strftime('%Y-%m-%d')}" if self.date_start and self.date_end else "no specific date range"
            
            prompt = prompt_template.format(
                folder_path=folder_path,
                folder_description=folder_description or f"Folder for {folder_path.split('/')[-1].replace('_', ' ').replace('-', ' ')}",
                industry=industry,
                date_range=date_range
            )
            
            # Get localized template label
            template_label = get_translation(
                "json_format_instructions.json_template_label", 
                self.settings.language
            )
            
            # Add JSON template to the prompt
            prompt = f"{prompt}\n\n{template_label}\n{json_template}"
            
            # Generate file metadata using LLM
            logging.info(f"Requesting file metadata for {folder_path} using LLM")
            file_data = self.llm_client.get_json_completion(
                prompt=prompt,
                max_attempts=3,
                language=self.settings.language
            )
            
            # Validate the returned data
            if not file_data or "name" not in file_data:
                logging.error(f"Failed to get valid file metadata for {folder_path}")
                return None
            
            # Ensure we have a type value
            if "type" not in file_data and "name" in file_data and "." in file_data["name"]:
                file_data["type"] = file_data["name"].split(".")[-1]
                
            # Ensure we have a description
            if "description" not in file_data:
                file_data["description"] = f"File related to {folder_path}"
                
            return file_data
            
        except Exception as e:
            logging.error(f"Error generating file metadata with LLM for {folder_path}: {e}")
            # Fail fast instead of providing fallback
            raise

    def _update_folder_metadata_with_llm(self, folder_path: str, folder_description: str, folder_metadata: Optional[Dict[str, Any]], industry: str, files_to_generate: int) -> Optional[Dict[str, Any]]:
        """
        Update folder metadata with suggestions from LLM.
        
        Args:
            folder_path: Path to the folder
            folder_description: Description of the folder
            folder_metadata: Current metadata for the folder
            industry: Industry context
            files_to_generate: Number of files to generate
            
        Returns:
            Updated metadata for the folder
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found
        """
        # Use LLM to generate suggestions for folder metadata
        prompt_template = get_translation("folder_structure_prompt.folder_metadata_prompt", self.settings.language)
        if not prompt_template:
            # No fallback - fail fast
            logging.error(f"Missing translation for folder_metadata_prompt in language {self.settings.language}")
            raise LocalizedTemplateNotFoundError(f"No translation found for folder_metadata_prompt in {self.settings.language}")
        
        # Get JSON template and localized descriptions
        json_template = JsonTemplates.get_template("folder_metadata")
        if not json_template:
            logging.error("Missing JSON template for folder_metadata")
            raise ValueError("JSON template not found for folder_metadata")
        
        # Get localized description templates
        folder_description_template = get_translation(
            "description_templates.folder_description", 
            self.settings.language
        )
        file_description_template = get_translation(
            "description_templates.file_description", 
            self.settings.language
        )
        
        # Apply localized descriptions to the template
        json_template = json_template.format(
            folder_description=folder_description_template,
            file_description=file_description_template
        )
        
        # Replace placeholders in the template
        date_range = self.date_range_str or f"{self.date_start.strftime('%Y-%m-%d')} to {self.date_end.strftime('%Y-%m-%d')}" if self.date_start and self.date_end else "no specific date range"
        
        prompt = prompt_template.format(
            folder_path=folder_path,
            folder_description=folder_description or f"Folder for {folder_path.split('/')[-1].replace('_', ' ').replace('-', ' ')}",
            industry=industry,
            date_range=date_range
        )
        
        # Get localized template label
        template_label = get_translation(
            "json_format_instructions.json_template_label", 
            self.settings.language
        )
        
        # Add JSON template to the prompt
        prompt = f"{prompt}\n\n{template_label}\n{json_template}"
        
        # Generate metadata using LLM
        logging.info(f"Requesting folder metadata for {folder_path} using LLM")
        metadata = self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3,
            language=self.settings.language
        )
        
        # Validate the returned data
        if not metadata or "description" not in metadata:
            logging.error(f"Failed to get valid folder metadata for {folder_path}")
            return None
        
        # Ensure we have a purpose
        if "purpose" not in metadata:
            metadata["purpose"] = "general"
        
        # Ensure we have a files list
        if "files" not in metadata:
            metadata["files"] = []
        
        # Generate file suggestions if none were returned by the LLM
        if not metadata["files"]:
            for _ in range(files_to_generate):
                try:
                    file_data = self._generate_random_file_data(folder_path, folder_description, industry)
                    if file_data and "name" in file_data:
                        metadata["files"].append(file_data)
                except Exception as e:
                    logging.error(f"Error generating file data: {e}")
                    # Continue even if individual file generation fails
                    continue
        
        return metadata
        
    def _reset_short_mode(self, short_mode: bool, mode: str = "all"):
        """
        Reset short mode settings for the current operation.
        
        Args:
            short_mode: Whether to enable short mode
            mode: Operation mode ('all', 'structure', or 'file')
        """
        self._short_mode_enabled = short_mode
        self._item_counts = {item_type: 0 for item_type in self.SHORT_MODE_LIMITS.keys()}
        
        # Log mode-specific info
        if short_mode:
            if mode == "all":
                logging.info(f"Short mode enabled: max {self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FOLDER]} folders and {self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FILE]} files")
            elif mode == "structure":
                logging.info(f"Short mode enabled: max {self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FOLDER]} folders")
            elif mode == "file":
                logging.info(f"Short mode enabled: max {self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FILE]} files")
        else:
            logging.info("Short mode disabled: no limit on folder and file count")
            
    def _check_short_mode_limit(self, item_type: str) -> bool:
        """
        Check if the short mode limit has been reached for the given item type.
        
        Args:
            item_type: Type of item to check ('folder', 'file', etc.)
            
        Returns:
            True if limit reached, False otherwise
        """
        if not self._short_mode_enabled:
            return False
            
        # Increment counter for this item type
        self._item_counts[item_type] = self._item_counts.get(item_type, 0) + 1
        
        # Check if limit reached
        if self._item_counts[item_type] > self.SHORT_MODE_LIMITS.get(item_type, 0):
            logging.info(f"Short mode limit reached for {item_type}s ({self._item_counts[item_type]-1})")
            return True
            
        return False
