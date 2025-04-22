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

from ..config.language_utils import get_translation
from ..content.content_generator import ContentGenerator
from ..content.file_manager import FileManager
from ..foundation.llm_client import OllamaClient
from ..statistics.statistics_tracker import StatisticsTracker
from ..config.settings import Settings


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
        date_format_template = get_translation("date_range_format", language, None)
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
        date_format_template = get_translation("date_range_format", language, None)
        
        # Check if we got back the key itself (which means translation wasn't found)
        # get_translation returns the key itself if default is None and translation isn't found
        if date_format_template == "date_range_format":
            error_msg = f"No localized template found for '{language}' language (date_range_format)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
        
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

    # --- Internal Processing Methods --- 
    # (These remain, with short mode checks already integrated)
    def _process_structure_only(self, level1_structure: Dict[str, Any], target_dir: Path,
                               industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Process the folder structure without files.
        
        Args:
            level1_structure: Level 1 folder structure data
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        # Store root level metadata
        root_metadata = {
            "industry": industry,
            "language": language,
            "role": role,
            "date_range": self.date_range_str,
            "date_start": self.date_start.strftime("%Y-%m-%d"),
            "date_end": self.date_end.strftime("%Y-%m-%d"),
            "folders": level1_structure["folders"]
        }
        self.file_manager.write_json_file(str(target_dir / ".metadata.json"), root_metadata)
        self.statistics_tracker.add_file(str(target_dir / ".metadata.json"))
        
        # Get parent folder names to check for conflicts
        parent_dirs = [p.name for p in target_dir.parents]
        
        for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
            if not isinstance(l1_folder_data, dict) or "description" not in l1_folder_data:
                logging.warning(f"Invalid data for folder {l1_folder_name}, skipping")
                continue
                
            # Check if folder name conflicts with parent folder name
            if l1_folder_name in parent_dirs:
                logging.warning(f"Folder name '{l1_folder_name}' conflicts with parent folder name, skipping")
                continue
                
            # Create level 1 folder
            l1_folder_path = target_dir / self.file_manager.sanitize_path(l1_folder_name)
            if not self.file_manager.ensure_directory(str(l1_folder_path)):
                success = False
                continue
                
            # Check limit after successfully creating L1 folder
            if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                
            # If folder already exists, proceed with content generation
            if l1_folder_path.exists():
                logging.info(f"Folder '{l1_folder_name}' already exists, proceeding with content generation")
                continue
                
            # Track folder
            self.statistics_tracker.add_folder(str(l1_folder_path))
                
            logging.info(f"Created level 1 folder: {l1_folder_name}")
            
            # Get folder purpose if specified
            folder_purpose = l1_folder_data.get("purpose")
            
            # Store level 1 folder metadata
            l1_metadata = {
                "name": l1_folder_name,
                "description": l1_folder_data.get("description", ""),
                "industry": industry,
                "purpose": folder_purpose
            }
            
            # Skip subfolder creation for timeseries folders
            if folder_purpose == "timeseries":
                logging.info(f"Folder {l1_folder_name} is marked as timeseries, skipping subfolders")
                self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
                self.statistics_tracker.add_file(str(l1_folder_path / ".metadata.json"))
                
                # Generate timeseries files for this folder
                self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}")
                self._generate_timeseries_files(
                    l1_folder_path, l1_folder_name, l1_folder_data.get("description", ""),
                    industry, language, role
                )
                self.statistics_tracker.end_tracking_item()
                continue
            
            # Generate level 2 folder structure
            self.statistics_tracker.start_tracking_item(f"level2_folders_for_{l1_folder_name}")
            level2_structure = self._generate_level2_folders(
                industry, l1_folder_name, l1_folder_data.get("description", ""), language, role
            )
            self.statistics_tracker.end_tracking_item()
            
            if not level2_structure or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping")
                continue
            
            # Add folders to level 1 metadata
            l1_metadata["folders"] = level2_structure["folders"]
            self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
            self.statistics_tracker.add_file(str(l1_folder_path / ".metadata.json"))
            
            # Track timeseries folders at level 2
            if self.content_generator.is_timeseries_limit_reached(str(l1_folder_path)):
                logging.warning(f"Maximum number of timeseries folders in {l1_folder_name} reached")
            
            # Update parent directories list for level 2 folder check
            l2_parent_dirs = parent_dirs + [l1_folder_name]
                
            # Process level 2 folders
            for l2_folder_name, l2_folder_data in level2_structure["folders"].items():
                if not isinstance(l2_folder_data, dict) or "description" not in l2_folder_data:
                    logging.warning(f"Invalid data for level 2 folder {l2_folder_name}, skipping")
                    continue
                    
                # Create level 2 folder
                l2_folder_path = l1_folder_path / self.file_manager.sanitize_path(l2_folder_name)
                if not self.file_manager.ensure_directory(str(l2_folder_path)):
                    success = False
                    continue
                    
                # Check limit after successfully creating L2 folder
                if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                
                logging.info(f"Created level 2 folder: {l1_folder_name}/{l2_folder_name}")
                
                # Get folder purpose if specified
                l2_folder_purpose = l2_folder_data.get("purpose")
                
                # Store level 2 folder metadata
                l2_metadata = {
                    "name": l2_folder_name,
                    "description": l2_folder_data.get("description", ""),
                    "parent_folder": l1_folder_name,
                    "industry": industry,
                    "purpose": l2_folder_purpose
                }
                
                # Skip subfolder creation for timeseries folders
                if l2_folder_purpose == "timeseries":
                    logging.info(f"Folder {l1_folder_name}/{l2_folder_name} is marked as timeseries, skipping subfolders")
                    self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                    
                    # Generate timeseries files for this folder
                    self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}_{l2_folder_name}")
                    self._generate_timeseries_files(
                        l2_folder_path, l2_folder_name, l2_folder_data.get("description", ""),
                        industry, language, role
                    )
                    self.statistics_tracker.end_tracking_item()
                
                # Generate level 3 folder structure
                level3_structure = self._generate_level3_folders(
                    industry, l2_folder_name, l2_folder_data, 
                    l1_folder_data.get("description", ""), l1_folder_name, language, role
                )
                
                if not level3_structure or "folders" not in level3_structure:
                    logging.warning(f"Failed to get valid level 3 structure for {l1_folder_name}/{l2_folder_name}, skipping")
                    continue
                
                # Add folders to level 2 metadata
                l2_metadata["folders"] = level3_structure["folders"]
                self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                self.statistics_tracker.add_file(str(l2_folder_path / ".metadata.json"))
                
                # Track timeseries folders at level 3
                if self.content_generator.is_timeseries_limit_reached(str(l2_folder_path)):
                    logging.warning(f"Maximum number of timeseries folders in {l1_folder_name}/{l2_folder_name} reached")
                
                # Update parent directories list for level 3 folder check
                l3_parent_dirs = l2_parent_dirs + [l2_folder_name]
                
                # Process level 3 folders
                for l3_folder_name, l3_folder_data in level3_structure["folders"].items():
                    if not isinstance(l3_folder_data, dict) or "description" not in l3_folder_data:
                        logging.warning(f"Invalid data for folder {l1_folder_name}/{l2_folder_name}/{l3_folder_name}, skipping")
                        continue
                        
                    # Create level 3 folder
                    l3_folder_path = l2_folder_path / self.file_manager.sanitize_path(l3_folder_name)
                    if not self.file_manager.ensure_directory(str(l3_folder_path)):
                        success = False
                        continue
                        
                    # Check limit after successfully creating L3 folder
                    if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                    
                    logging.info(f"Created level 3 folder: {l1_folder_name}/{l2_folder_name}/{l3_folder_name}")
                    
                    # Store level 3 folder metadata
                    l3_metadata = {
                        "name": l3_folder_name,
                        "description": l3_folder_data.get("description", ""),
                        "parent_folder": l2_folder_name,
                        "grandparent_folder": l1_folder_name,
                        "industry": industry,
                        "purpose": l3_folder_data.get("purpose")
                    }
                    self.file_manager.write_json_file(str(l3_folder_path / ".metadata.json"), l3_metadata)
                    self.statistics_tracker.add_file(str(l3_folder_path / ".metadata.json"))
                    
                    # Generate timeseries files for timeseries folders
                    if l3_folder_data.get("purpose") == "timeseries":
                        logging.info(f"Folder {l1_folder_name}/{l2_folder_name}/{l3_folder_name} is marked as timeseries")
                        self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}_{l2_folder_name}_{l3_folder_name}")
                        try:
                            self._generate_timeseries_files(
                                l3_folder_path, l3_folder_name, l3_folder_data.get("description", ""),
                                industry, language, role
                            )
                        except ShortModeLimitReached:
                            # Re-raise to handle at the generate_files_only level
                            raise
                        finally:
                            self.statistics_tracker.end_tracking_item()
        
        logging.info("Folder structure creation completed (or stopped by short mode).")
        return success
    
    def _process_folder_structure(self, level1_structure: Dict[str, Any], target_dir: Path,
                                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Process the folder structure and generate files.
        
        Args:
            level1_structure: Level 1 folder structure data
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        # Store root level metadata
        root_metadata = {
            "industry": industry,
            "language": language,
            "role": role,
            "date_range": self.date_range_str,
            "date_start": self.date_start.strftime("%Y-%m-%d"),
            "date_end": self.date_end.strftime("%Y-%m-%d"),
            "folders": level1_structure["folders"]
        }
        self.file_manager.write_json_file(str(target_dir / ".metadata.json"), root_metadata)
        self.statistics_tracker.add_file(str(target_dir / ".metadata.json"))
        
        # Get parent folder names to check for conflicts
        parent_dirs = [p.name for p in target_dir.parents]
        
        for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
            if not isinstance(l1_folder_data, dict) or "description" not in l1_folder_data:
                logging.warning(f"Invalid data for folder {l1_folder_name}, skipping")
                continue
                
            # Check if folder name conflicts with parent folder name
            if l1_folder_name in parent_dirs:
                logging.warning(f"Folder name '{l1_folder_name}' conflicts with parent folder name, skipping")
                continue
                
            # Create level 1 folder
            l1_folder_path = target_dir / self.file_manager.sanitize_path(l1_folder_name)
            if not self.file_manager.ensure_directory(str(l1_folder_path)):
                success = False
                continue
                
            # Check limit after successfully creating L1 folder
            if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                
            # If folder already exists, proceed with content generation
            if l1_folder_path.exists():
                logging.info(f"Folder '{l1_folder_name}' already exists, proceeding with content generation")
                continue
                
            # Track folder creation
            self.statistics_tracker.add_folder(str(l1_folder_path))
                
            logging.info(f"Created level 1 folder: {l1_folder_name}")
            
            # Get folder purpose if specified
            folder_purpose = l1_folder_data.get("purpose")
            
            # Store level 1 folder metadata
            l1_metadata = {
                "name": l1_folder_name,
                "description": l1_folder_data.get("description", ""),
                "industry": industry,
                "purpose": folder_purpose
            }
            
            # Skip subfolder creation for timeseries folders
            if folder_purpose == "timeseries":
                logging.info(f"Folder {l1_folder_name} is marked as timeseries, skipping subfolders")
                self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
                self.statistics_tracker.add_file(str(l1_folder_path / ".metadata.json"))
                
                # Generate timeseries files for this folder
                self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}")
                self._generate_timeseries_files(
                    l1_folder_path, l1_folder_name, l1_folder_data.get("description", ""),
                    industry, language, role
                )
                self.statistics_tracker.end_tracking_item()
                continue
            
            # Generate level 2 folder structure
            self.statistics_tracker.start_tracking_item(f"level2_folders_for_{l1_folder_name}")
            level2_structure = self._generate_level2_folders(
                industry, l1_folder_name, l1_folder_data.get("description", ""), language, role
            )
            self.statistics_tracker.end_tracking_item()
            
            if not level2_structure or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping subfolders")
                continue
            
            # Add folders to level 1 metadata
            l1_metadata["folders"] = level2_structure["folders"]
            self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
            self.statistics_tracker.add_file(str(l1_folder_path / ".metadata.json"))
            
            # Process level 2 folders
            for l2_folder_name, l2_folder_data in level2_structure["folders"].items():
                if not isinstance(l2_folder_data, dict) or "description" not in l2_folder_data:
                    logging.warning(f"Invalid data for folder {l1_folder_name}/{l2_folder_name}, skipping")
                    continue
                    
                # Create level 2 folder
                l2_folder_path = l1_folder_path / self.file_manager.sanitize_path(l2_folder_name)
                if not self.file_manager.ensure_directory(str(l2_folder_path)):
                    success = False
                    continue
                    
                # Check limit after successfully creating L2 folder
                if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                
                logging.info(f"Created level 2 folder: {l1_folder_name}/{l2_folder_name}")
                
                # Get folder purpose if specified
                l2_folder_purpose = l2_folder_data.get("purpose")
                
                # Store level 2 folder metadata
                l2_metadata = {
                    "name": l2_folder_name,
                    "description": l2_folder_data.get("description", ""),
                    "industry": industry,
                    "parent": l1_folder_name,
                    "purpose": l2_folder_purpose
                }
                
                # Skip subfolder creation for timeseries folders
                if l2_folder_purpose == "timeseries":
                    logging.info(f"Folder {l1_folder_name}/{l2_folder_name} is marked as timeseries, skipping subfolders")
                    self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                    self.statistics_tracker.add_file(str(l2_folder_path / ".metadata.json"))
                    
                    # Generate timeseries files for this folder
                    self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}_{l2_folder_name}")
                    self._generate_timeseries_files(
                        l2_folder_path, l2_folder_name, l2_folder_data.get("description", ""),
                        industry, language, role
                    )
                    self.statistics_tracker.end_tracking_item()
                
                # Generate level 3 folder structure
                self.statistics_tracker.start_tracking_item(f"level3_folders_for_{l1_folder_name}_{l2_folder_name}")
                level3_structure = self._generate_level3_folders(
                    industry, l2_folder_name, l2_folder_data, l1_folder_data.get("description", ""),
                    l1_folder_name, language, role
                )
                self.statistics_tracker.end_tracking_item()
                
                if level3_structure and "folders" in level3_structure:
                    # Add folders to level 2 metadata
                    l2_metadata["folders"] = level3_structure["folders"]
                    self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                    self.statistics_tracker.add_file(str(l2_folder_path / ".metadata.json"))
                    
                    # Process level 3 folders
                    for l3_folder_name, l3_folder_data in level3_structure["folders"].items():
                        if not isinstance(l3_folder_data, dict) or "description" not in l3_folder_data:
                            logging.warning(f"Invalid data for folder {l1_folder_name}/{l2_folder_name}/{l3_folder_name}, skipping")
                            continue
                            
                        # Create level 3 folder
                        l3_folder_path = l2_folder_path / self.file_manager.sanitize_path(l3_folder_name)
                        if not self.file_manager.ensure_directory(str(l3_folder_path)):
                            success = False
                            continue
                            
                        # Check limit after successfully creating L3 folder
                        if self._check_short_mode_limit(self.ITEM_TYPE_FOLDER): raise ShortModeLimitReached()
                        
                        logging.info(f"Created level 3 folder: {l1_folder_name}/{l2_folder_name}/{l3_folder_name}")
                        
                        # Store level 3 folder metadata
                        l3_metadata = {
                            "name": l3_folder_name,
                            "description": l3_folder_data.get("description", ""),
                            "industry": industry,
                            "parent": l2_folder_name,
                            "grandparent": l1_folder_name,
                            "purpose": l3_folder_data.get("purpose")
                        }
                        self.file_manager.write_json_file(str(l3_folder_path / ".metadata.json"), l3_metadata)
                        self.statistics_tracker.add_file(str(l3_folder_path / ".metadata.json"))
                        
                        # Generate timeseries files for timeseries folders
                        if l3_folder_data.get("purpose") == "timeseries":
                            logging.info(f"Folder {l1_folder_name}/{l2_folder_name}/{l3_folder_name} is marked as timeseries")
                            self.statistics_tracker.start_tracking_item(f"timeseries_files_for_{l1_folder_name}_{l2_folder_name}_{l3_folder_name}")
                            try:
                                self._generate_timeseries_files(
                                    l3_folder_path, l3_folder_name, l3_folder_data.get("description", ""),
                                    industry, language, role
                                )
                            except ShortModeLimitReached:
                                # Re-raise to handle at the generate_files_only level
                                raise
                            finally:
                                self.statistics_tracker.end_tracking_item()
                
                # Generate files for level 2 folder
                self.statistics_tracker.start_tracking_item(f"files_for_{l1_folder_name}_{l2_folder_name}")
                level2_files = self._generate_level3_files(
                    industry, l2_folder_name, l2_folder_data, l1_folder_data.get("description", ""),
                    l1_folder_name, language, role
                )
                self.statistics_tracker.end_tracking_item()
                
                if level2_files and "files" in level2_files:
                    # Add files to level 2 metadata
                    l2_metadata["files"] = level2_files["files"]
                    
                    # Write updated metadata
                    self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                    self.statistics_tracker.add_file(str(l2_folder_path / ".metadata.json"))
                    
                    # Create files
                    self.statistics_tracker.start_tracking_item(f"file_content_for_{l1_folder_name}_{l2_folder_name}")
                    
                    # Check if files is a list or dictionary and handle accordingly
                    if isinstance(level2_files["files"], list):
                        logging.info(f"Files for {l1_folder_name}/{l2_folder_name} provided as a list, converting to dictionary")
                        files_dict = {}
                        for file_data in level2_files["files"]:
                            if isinstance(file_data, dict) and "name" in file_data:
                                files_dict[file_data["name"]] = {k: v for k, v in file_data.items() if k != "name"}
                        level2_files["files"] = files_dict
                    
                    # Process the files
                    for file_name, file_data in level2_files["files"].items():
                        if not isinstance(file_data, dict) or "type" not in file_data:
                            logging.warning(f"Invalid data for file {l1_folder_name}/{l2_folder_name}/{file_name}, skipping")
                            continue
                        
                        # Generate content for the file
                        try:
                            file_path = l2_folder_path / self.file_manager.sanitize_path(file_name)
                            
                            # Skip existing files
                            if self.file_manager.file_exists(str(file_path)):
                                logging.info(f"File {file_path} already exists, skipping")
                                continue
                            
                            content_success = self.content_generator.generate_file_content(
                                str(file_path),
                                file_data.get("type", ""),
                                file_data.get("description", ""),
                                industry,
                                f"{l1_folder_name}/{l2_folder_name}",
                                language,
                                role
                            )
                            
                            if content_success:
                                # Track file creation
                                self.statistics_tracker.add_file(str(file_path))
                                
                                # Check file limit after successfully creating a file
                                if self._check_short_mode_limit(self.ITEM_TYPE_FILE): 
                                    logging.info(f"Short mode file limit reached after creating {file_name}")
                                    raise ShortModeLimitReached()
                        except Exception as e:
                            logging.error(f"Error generating file {file_name}: {e}")
                    self.statistics_tracker.end_tracking_item()
                else:
                    # Just update the metadata without files
                    self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                    self.statistics_tracker.add_file(str(l2_folder_path / ".metadata.json"))
        
        logging.info("Folder structure and file creation completed (or stopped by short mode).")
        return success
    
    def _regenerate_files(self, target_dir: Path, industry: str, language: str, 
                        role: Optional[str] = None) -> bool:
        """
        Regenerate files for existing folder structure.
        
        Args:
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        files_generated = 0
        
        # Get parent folder names to check for conflicts
        parent_dirs = [p.name for p in target_dir.parents]
        
        # Check for root metadata but don't fail if missing in file mode
        root_metadata = None
        if (target_dir / ".metadata.json").exists():
            root_metadata = self.file_manager.read_json_file(str(target_dir / ".metadata.json"))
            if root_metadata:
                logging.info("Found root metadata file")
                # Update with values from metadata if available
                if "industry" in root_metadata:
                    industry = root_metadata["industry"]
                if "language" in root_metadata:
                    language = root_metadata["language"]
                if "role" in root_metadata:
                    role = root_metadata["role"]
                
                # Update date range information if present in metadata
                if "date_range" in root_metadata:
                    logging.info(f"Using date range from metadata: {root_metadata['date_range']}")
                    self.date_range_str = root_metadata["date_range"]
                    
                    # Try to parse date range from metadata if available
                    if "date_start" in root_metadata and "date_end" in root_metadata:
                        try:
                            self.date_start = datetime.strptime(root_metadata["date_start"], "%Y-%m-%d")
                            self.date_end = datetime.strptime(root_metadata["date_end"], "%Y-%m-%d")
                            logging.info(f"Parsed date range: {self.date_start.strftime('%Y-%m-%d')} to {self.date_end.strftime('%Y-%m-%d')}")
                        except ValueError:
                            logging.warning("Could not parse dates from metadata, using default date range")
        else:
            logging.warning("Root metadata file not found, using provided parameters")
            
        try:
            # Keep track of total files generated across all folders
            total_files_generated = 0
            
            # Process level 1 folders
            for level1_item in target_dir.iterdir():
                if not level1_item.is_dir() or level1_item.name.startswith('.'):
                    continue
                    
                # Process this folder even if no metadata, since we're in file mode
                logging.info(f"Processing folder: {level1_item.name}")
                
                # Try to read metadata if available, but continue even if missing
                l1_metadata = None
                l1_description = ""
                l1_purpose = None
                
                l1_metadata_path = level1_item / ".metadata.json"
                if l1_metadata_path.exists():
                    l1_metadata = self.file_manager.read_json_file(str(l1_metadata_path))
                    if l1_metadata:
                        l1_description = l1_metadata.get("description", "")
                        l1_purpose = l1_metadata.get("purpose")
                else:
                    logging.info(f"No metadata for {level1_item.name}, using defaults")
                    # Provide default description based on folder name
                    l1_description = f"Files for {level1_item.name} folder"
                
                # Generate simple document files for this folder
                if not l1_purpose == "timeseries":
                    logging.info(f"Generating files for {level1_item.name}")
                    try:
                        # Generate files using the LLM instead of fixed defaults
                        # Use the level3_files_prompt which is designed for file generation
                        prompt_template = get_translation("folder_structure_prompt.level3_files_prompt", language, None)
                        
                        if not prompt_template:
                            logging.error(f"No file generation prompt found for language '{language}'")
                            continue
                            
                        # Format prompt with folder information
                        role_text = f" for a {role}" if role else ""
                        prompt = prompt_template.format(
                            industry=industry,
                            l1_folder_name=level1_item.name,
                            l1_description=l1_description,
                            l2_folder_name="",  # No L2 folder in this context
                            l2_description="",  # No L2 folder in this context
                            folder_structure="",  # No subfolders to consider
                            role_text=role_text,
                            industry_info=""  # No specific industry info provided
                        )
                        
                        # Generate files structure using LLM
                        logging.info(f"Requesting file structure for {level1_item.name} using LLM")
                        file_structure = self.llm_client.get_json_completion(
                            prompt=prompt,
                            max_attempts=3
                        )
                        
                        # Process the file structure
                        if not file_structure or "files" not in file_structure:
                            logging.warning(f"Failed to get valid file structure for {level1_item.name}")
                            continue
                            
                        # Handle both list and dict format for files
                        default_files = []
                        if isinstance(file_structure["files"], list):
                            default_files = file_structure["files"]
                        elif isinstance(file_structure["files"], dict):
                            for file_name, file_data in file_structure["files"].items():
                                if isinstance(file_data, dict):
                                    file_data["name"] = file_name
                                    default_files.append(file_data)
                        
                        logging.info(f"Generated {len(default_files)} files for {level1_item.name}")
                        
                        # Update metadata with new files
                        if l1_metadata and isinstance(l1_metadata, dict):
                            if "files" not in l1_metadata:
                                l1_metadata["files"] = {}
                                
                            # Add generated files to metadata
                            for file_data in default_files:
                                if isinstance(file_data, dict) and "name" in file_data:
                                    file_name = file_data["name"]
                                    l1_metadata["files"][file_name] = {k: v for k, v in file_data.items() if k != "name"}
                            
                            # Write updated metadata
                            self.file_manager.write_json_file(str(l1_metadata_path), l1_metadata)
                            logging.info(f"Updated metadata for {level1_item.name} with new files")
                        
                        if not default_files:
                            logging.warning(f"No valid files were generated for folder '{level1_item.name}'")
                            continue
                            
                        # Now create the actual files
                        for file_data in default_files:
                            if not isinstance(file_data, dict) or "name" not in file_data:
                                continue
                                
                            file_path = level1_item / file_data["name"]
                            
                            # Skip if file already exists
                            if file_path.exists():
                                logging.info(f"File {file_data['name']} already exists, skipping")
                                continue
                            
                            # Get file type from extension or explicit type field
                            file_type = file_data.get("type", "")
                            if not file_type and "." in file_data["name"]:
                                file_type = file_data["name"].split(".")[-1]
                            
                            # Generate file content
                            success = self.content_generator.generate_file_content(
                                str(file_path),
                                file_type,
                                file_data.get("description", ""),
                                industry,
                                level1_item.name,
                                language,
                                role
                            )
                            
                            if success:
                                total_files_generated += 1
                                self.statistics_tracker.add_file(str(file_path))
                                logging.info(f"Created file: {level1_item.name}/{file_data['name']} (total: {total_files_generated})")
                                
                                # Check file limit after successfully creating a file
                                if self._check_short_mode_limit(self.ITEM_TYPE_FILE): 
                                    logging.info(f"Short mode file limit reached after creating {total_files_generated} files")
                                    return True
                    except ShortModeLimitReached:
                        # Limit reached, exit successfully
                        return True
                else:
                    # Handle timeseries folders
                    logging.info(f"Generating timeseries files for {level1_item.name}")
                    try:
                        self._generate_timeseries_files(
                            level1_item, level1_item.name, l1_description,
                            industry, language, role
                        )
                    except ShortModeLimitReached:
                        # Re-raise to handle at the generate_files_only level
                        return True
                
                # Process level 2 folders if this folder doesn't have enough files yet
                if self._short_mode_enabled and total_files_generated >= self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FILE]:
                    logging.info(f"File limit reached ({total_files_generated} files), stopping")
                    return True
                    
                for level2_item in level1_item.iterdir():
                    if not level2_item.is_dir() or level2_item.name.startswith('.'):
                        continue
                    
                    logging.info(f"Processing subfolder: {level1_item.name}/{level2_item.name}")
                    
                    # Try to read metadata but continue even if missing
                    l2_metadata = None
                    l2_description = ""
                    l2_purpose = None
                    
                    l2_metadata_path = level2_item / ".metadata.json"
                    if l2_metadata_path.exists():
                        l2_metadata = self.file_manager.read_json_file(str(l2_metadata_path))
                        if l2_metadata:
                            l2_description = l2_metadata.get("description", "")
                            l2_purpose = l2_metadata.get("purpose")
                    else:
                        logging.info(f"No metadata for {level1_item.name}/{level2_item.name}, using defaults")
                        l2_description = f"Files for {level2_item.name} folder"

                    # Generate files for this level 2 folder
                    if not l2_purpose == "timeseries":
                        logging.info(f"Generating files for {level1_item.name}/{level2_item.name}")
                        try:
                            # Use the level3_files_prompt which is designed for file generation
                            prompt_template = get_translation("folder_structure_prompt.level3_files_prompt", language, None)
                            
                            if not prompt_template:
                                logging.error(f"No file generation prompt found for language '{language}'")
                                continue
                                
                            # Format prompt with folder information
                            role_text = f" for a {role}" if role else ""
                            prompt = prompt_template.format(
                                industry=industry,
                                l1_folder_name=level1_item.name,
                                l1_description=l1_description,
                                l2_folder_name=level2_item.name,
                                l2_description=l2_description,
                                folder_structure="",  # No subfolders to consider
                                role_text=role_text,
                                industry_info=""  # No specific industry info provided
                            )
                            
                            # Generate files structure using LLM
                            logging.info(f"Requesting file structure for {level1_item.name}/{level2_item.name} using LLM")
                            file_structure = self.llm_client.get_json_completion(
                                prompt=prompt,
                                max_attempts=3
                            )
                            
                            # Process the file structure
                            if not file_structure or "files" not in file_structure:
                                logging.warning(f"Failed to get valid file structure for {level1_item.name}/{level2_item.name}")
                                continue
                                
                            # Handle both list and dict format for files
                            default_files = []
                            if isinstance(file_structure["files"], list):
                                default_files = file_structure["files"]
                            elif isinstance(file_structure["files"], dict):
                                for file_name, file_data in file_structure["files"].items():
                                    if isinstance(file_data, dict):
                                        file_data["name"] = file_name
                                        default_files.append(file_data)
                            
                            logging.info(f"Generated {len(default_files)} files for {level1_item.name}/{level2_item.name}")
                            
                            # Update metadata with new files
                            if l2_metadata and isinstance(l2_metadata, dict):
                                if "files" not in l2_metadata:
                                    l2_metadata["files"] = {}
                                    
                                # Add generated files to metadata
                                for file_data in default_files:
                                    if isinstance(file_data, dict) and "name" in file_data:
                                        file_name = file_data["name"]
                                        l2_metadata["files"][file_name] = {k: v for k, v in file_data.items() if k != "name"}
                                
                                # Write updated metadata
                                self.file_manager.write_json_file(str(l2_metadata_path), l2_metadata)
                                logging.info(f"Updated metadata for {level1_item.name}/{level2_item.name} with new files")
                            
                            if not default_files:
                                logging.warning(f"No valid files were generated for folder '{level1_item.name}/{level2_item.name}'")
                                continue
                                
                            # Now create the actual files
                            for file_data in default_files:
                                if not isinstance(file_data, dict) or "name" not in file_data:
                                    continue
                                    
                                file_path = level2_item / file_data["name"]
                                
                                # Skip if file already exists
                                if file_path.exists():
                                    logging.info(f"File {file_data['name']} already exists, skipping")
                                    continue
                                
                                # Get file type from extension or explicit type field
                                file_type = file_data.get("type", "")
                                if not file_type and "." in file_data["name"]:
                                    file_type = file_data["name"].split(".")[-1]
                                
                                # Generate file content
                                success = self.content_generator.generate_file_content(
                                    str(file_path),
                                    file_type,
                                    file_data.get("description", ""),
                                    industry,
                                    f"{level1_item.name}/{level2_item.name}",
                                    language,
                                    role
                                )
                                
                                if success:
                                    total_files_generated += 1
                                    self.statistics_tracker.add_file(str(file_path))
                                    logging.info(f"Created file: {level1_item.name}/{level2_item.name}/{file_data['name']} (total: {total_files_generated})")
                                    
                                    # Check file limit after successfully creating a file
                                    if self._check_short_mode_limit(self.ITEM_TYPE_FILE): 
                                        logging.info(f"Short mode file limit reached after creating {total_files_generated} files")
                                        return True
                        except ShortModeLimitReached:
                            return True
                        except Exception as e:
                            logging.error(f"Error generating files for {level1_item.name}/{level2_item.name}: {e}")
                    else:
                        # Handle timeseries folders
                        logging.info(f"Generating timeseries files for {level1_item.name}/{level2_item.name}")
                        try:
                            self._generate_timeseries_files(
                                level2_item, level2_item.name, l2_description,
                                industry, language, role
                            )
                        except ShortModeLimitReached:
                            # Re-raise to handle at the generate_files_only level
                            return True
            
            if total_files_generated == 0:
                logging.warning("No files were generated. Check your folder structure.")
                return False
                
            logging.info(f"Successfully generated {total_files_generated} files in file mode")
            return success
            
        except Exception as e:
            logging.exception(f"Error during file regeneration: {e}")
            return False
    
    # --- LLM Interaction and Prompt Generation --- 
    def _generate_level1_folders(self, industry: str, language: str, 
                               role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate level 1 folder structure using LLM.
        """
        prompt = self._get_level1_folders_prompt(industry, language, role)
        if not prompt:
            logging.error("Failed to generate prompt for level 1 folders.")
            # Return an empty structure or None to indicate failure
            return {"folders": {}} 
        
        return self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3
        )
    
    def _generate_level2_folders(self, industry: str, l1_folder_name: str, 
                               l1_description: str, language: str, 
                               role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate level 2 folder structure.
        
        Args:
            industry: Industry context
            l1_folder_name: Level 1 folder name
            l1_description: Level 1 folder description
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Dictionary with folder structure information
        """
        prompt = self._get_level2_folders_prompt(industry, l1_folder_name, l1_description, language, role)
        
        return self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3
        )
    
    def _get_level1_folders_prompt(self, industry: str, language: str, role: Optional[str] = None) -> str:
        """
        Get prompt for level 1 folder generation.
        
        Args:
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Prompt string
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the specified language
        """
        # Use get_translation to get the localized prompt from resources
        prompt_template = get_translation("folder_structure_prompt.level1", language, None)
        
        # If no translated template found, raise an exception
        if not prompt_template:
            error_msg = f"No localized template found for '{language}' language (folder_structure_prompt.level1)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
        
        # Role placeholder might be formatted differently in localized templates
        # so we'll use the role_text format from the language templates
        role_text = f" for a {role}" if role else ""
        
        # Format date range for the prompt
        date_range = self.date_range_str
        
        # Replace placeholders in the template
        prompt = prompt_template.format(
            industry=industry,
            role_text=role_text,
            date_range=date_range
        )
        
        return prompt
    
    def _get_level2_folders_prompt(self, industry: str, l1_folder_name: str, 
                                 l1_description: str, language: str, 
                                 role: Optional[str] = None) -> str:
        """
        Get prompt for level 2 folder generation.
        
        Args:
            industry: Industry context
            l1_folder_name: Level 1 folder name
            l1_description: Level 1 folder description
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Prompt string
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the specified language
        """
        # Use get_translation to get the localized prompt from resources
        prompt_template = get_translation("folder_structure_prompt.level2", language, None)
        
        # If no translated template found, raise an exception
        if not prompt_template:
            error_msg = f"No localized template found for '{language}' language (folder_structure_prompt.level2)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
        
        # Role placeholder might be formatted differently in localized templates
        role_text = f" for a {role}" if role else ""
        
        # Replace placeholders in the template
        prompt = prompt_template.format(
            industry=industry,
            l1_folder_name=l1_folder_name,
            l1_description=l1_description,
            role_text=role_text,
            date_range=self.date_range_str
        )
        
        return prompt
    
    def _generate_level3_folders(self, industry: str, l2_folder_name: str, 
                               l2_folder_data: Dict[str, Any], l1_description: str,
                               l1_folder_name: str, language: str, 
                               role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate level 3 folder structure.
        
        Args:
            industry: Industry context
            l2_folder_name: Level 2 folder name
            l2_folder_data: Level 2 folder data
            l1_description: Level 1 folder description
            l1_folder_name: Level 1 folder name
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Dictionary with folder structure information
        """
        prompt = self._get_level3_folders_prompt(industry, l2_folder_name, l2_folder_data, 
                                               l1_description, l1_folder_name, language, role)
        
        return self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3
        )
    
    def _get_level3_folders_prompt(self, industry: str, l2_folder_name: str, 
                                 l2_folder_data: Dict[str, Any], l1_description: str,
                                 l1_folder_name: str, language: str, 
                                 role: Optional[str] = None) -> str:
        """
        Get prompt for level 3 folder generation.
        
        Args:
            industry: Industry context
            l2_folder_name: Level 2 folder name
            l2_folder_data: Level 2 folder data
            l1_description: Level 1 folder description
            l1_folder_name: Level 1 folder name
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Prompt string
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the specified language
        """
        l2_description = l2_folder_data.get("description", "")
        
        # Use get_translation to get the localized prompt from resources
        prompt_template = get_translation("folder_structure_prompt.level3", language, None)
        
        # If no translated template found, raise an exception
        if not prompt_template:
            error_msg = f"No localized template found for '{language}' language (folder_structure_prompt.level3)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
        
        # Role placeholder might be formatted differently in localized templates
        role_text = f" for a {role}" if role else ""
        
        # Replace placeholders in the template
        prompt = prompt_template.format(
            industry=industry,
            l1_folder_name=l1_folder_name,
            l1_description=l1_description,
            l2_folder_name=l2_folder_name,
            l2_description=l2_description,
            role_text=role_text,
            date_range=self.date_range_str
        )
        
        return prompt
    
    def _generate_level3_files(self, industry: str, l2_folder_name: str, 
                             l2_folder_data: Dict[str, Any], l1_description: str,
                             l1_folder_name: str, language: str, 
                             role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate level 3 files structure.
        
        Args:
            industry: Industry context
            l2_folder_name: Level 2 folder name
            l2_folder_data: Level 2 folder data
            l1_description: Level 1 folder description
            l1_folder_name: Level 1 folder name
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Dictionary with files information
        """
        prompt = self._get_level3_files_prompt(industry, l2_folder_name, l2_folder_data, 
                                             l1_description, l1_folder_name, language, role)
        
        return self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3
        )
    
    def _get_level3_files_prompt(self, industry: str, l2_folder_name: str, 
                               l2_folder_data: Dict[str, Any], l1_description: str,
                               l1_folder_name: str, language: str, 
                               role: Optional[str] = None) -> str:
        """
        Get prompt for level 3 files generation.
        
        Args:
            industry: Industry context
            l2_folder_name: Level 2 folder name
            l2_folder_data: Level 2 folder data
            l1_description: Level 1 folder description
            l1_folder_name: Level 1 folder name
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Prompt string
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the specified language
        """
        l2_description = l2_folder_data.get("description", "")
        
        # Get folder structure from level 2 data if available
        folder_structure = ""
        if "folders" in l2_folder_data and l2_folder_data["folders"]:
            folder_names = ", ".join([f'"{name}"' for name in l2_folder_data["folders"].keys()])
            folder_structure = f"[{folder_names}]"
        
        # Use get_translation to get the localized prompt from resources
        prompt_template = get_translation("folder_structure_prompt.level3_files_prompt", language, None)
        
        # If no translated template found, raise an exception
        if not prompt_template:
            error_msg = f"No localized template found for '{language}' language (folder_structure_prompt.level3_files_prompt)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
            
        # Role placeholder might be formatted differently in localized templates
        role_text = f" for a {role}" if role else ""
        
        # Get industry info if available
        industry_info = ""
        
        # Replace placeholders in the template
        prompt = prompt_template.format(
            industry=industry,
            industry_info=industry_info,
            l1_folder_name=l1_folder_name,
            l1_description=l1_description,
            l2_folder_name=l2_folder_name,
            l2_description=l2_description,
            folder_structure=folder_structure,
            role_text=role_text,
            date_range=self.date_range_str
        )
        
        return prompt
        
    def _generate_timeseries_files(self, folder_path: Path, folder_name: str, folder_description: str,
                                 industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Generate timeseries files for a folder marked with timeseries purpose.
        
        Args:
            folder_path: Path to the folder
            folder_name: Name of the folder
            folder_description: Description of the folder
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LocalizedTemplateNotFoundError: If no localized template is found for the specified language
        """
        # Get localized prompt template
        prompt_template = get_translation("folder_structure_prompt.timeseries_files_prompt", language, None)
        
        # If no translated template found, raise an exception
        if not prompt_template:
            error_msg = f"No localized template found for '{language}' language (folder_structure_prompt.timeseries_files_prompt)"
            logging.error(error_msg)
            raise LocalizedTemplateNotFoundError(error_msg)
            
        # Replace placeholders in the template
        role_text = f" for a {role}" if role else ""
        prompt = prompt_template.format(
            folder_name=folder_name,
            folder_description=folder_description,
            industry=industry,
            language=language,
            role_text=role_text,
            date_range=self.date_range_str
        )
        
        file_structure = self.llm_client.get_json_completion(
            prompt=prompt,
            max_attempts=3
        )
        
        if not file_structure or "files" not in file_structure:
            logging.error(f"Failed to get valid file structure for timeseries folder {folder_name}")
            return False
            
        success = True
        
        # Create each file
        for file_info in file_structure["files"]:
            try:
                if not isinstance(file_info, dict) or "name" not in file_info:
                    continue
                    
                file_name = file_info["name"]
                file_description = file_info.get("description", "")
                
                self.content_generator.generate_file(
                    str(folder_path), file_name, file_description,
                    industry, language, role, purpose="timeseries"
                )
                logging.info(f"Created timeseries file: {folder_path}/{file_name}")
                
                # Check file limit after successfully creating a file
                if self._check_short_mode_limit(self.ITEM_TYPE_FILE): 
                    logging.info(f"Short mode file limit reached after creating {file_name}")
                    raise ShortModeLimitReached()
            except Exception as e:
                logging.error(f"Error creating timeseries file: {e}")
                success = False
                
        return success

    def _check_short_mode_limit(self, item_type: str) -> bool:
        """
        Checks if the short mode limit has been reached for the specified item type.
        
        Args:
            item_type: Type of item to check (must be one of the ITEM_TYPE_* constants)
            
        Returns:
            True if limit reached, False otherwise
        """
        if not self._short_mode_enabled:
            return False # Short mode not active

        if item_type not in self.SHORT_MODE_LIMITS:
            logging.warning(f"Unknown item type '{item_type}' in short mode check")
            return False

        limit = self.SHORT_MODE_LIMITS[item_type]
        if limit == 0:  # No limit for this item type
            logging.debug(f"No limit set for item type '{item_type}', continuing")
            return False

        # Get caller info for debugging
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_function = caller_frame.f_code.co_name if caller_frame else "unknown"
        caller_line = caller_frame.f_lineno if caller_frame else 0
        
        # Log every check with caller information
        logging.debug(f"Checking {item_type} limit ({self._item_counts[item_type]}/{limit}) - called from {caller_function}:{caller_line}")

        if self._item_counts[item_type] >= limit:
            logging.info(f"Short mode {item_type} limit ({limit} {item_type}s) reached - called from {caller_function}:{caller_line}")
            return True # Limit reached
        
        self._item_counts[item_type] += 1
        logging.info(f"Short mode {item_type} count: {self._item_counts[item_type]}/{limit} - called from {caller_function}:{caller_line}")
        return False # Limit not reached

    def _reset_short_mode(self, short_mode: bool, mode: str = "all"):
        """
        Resets the counters and sets the mode for a new run.
        
        Args:
            short_mode: Whether to enable short mode
            mode: The generation mode ('all', 'structure', or 'file')
        """
        self._item_counts = {item_type: 0 for item_type in self.SHORT_MODE_LIMITS.keys()}
        self._short_mode_enabled = short_mode
        
        # For file-only mode, disable folder limits
        if mode == "file" and short_mode:
            self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FOLDER] = 0  # Disable folder limit in file mode
            logging.info("File mode: folder limit disabled")
        elif short_mode:
            # Reset to default limits for other modes
            self.SHORT_MODE_LIMITS[self.ITEM_TYPE_FOLDER] = 10
            
        if short_mode:
            limits_str = ", ".join(f"{limit} {item_type}s" for item_type, limit in self.SHORT_MODE_LIMITS.items() if limit > 0)
            logging.info(f"Short mode enabled (limits: {limits_str}).")
            
        # Add debug logging for current limits
        for item_type, limit in self.SHORT_MODE_LIMITS.items():
            logging.debug(f"Short mode limit for {item_type}: {limit}")
            
        # Log current date range information
        logging.info(f"Using date range: {self.date_range_str} for content generation")
