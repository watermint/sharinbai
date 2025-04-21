"""
Folder structure generator
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.foundation.llm_client import OllamaClient
from src.content.file_manager import FileManager
from src.content.content_generator import ContentGenerator

class FolderGenerator:
    """Generates folder structures and instructs content creation"""
    
    def __init__(self, model: str = "llama3", ollama_url: Optional[str] = None):
        """
        Initialize the folder generator.
        
        Args:
            model: Model name to use for generation
            ollama_url: URL for the Ollama API server
        """
        self.llm_client = OllamaClient(model, ollama_url)
        self.file_manager = FileManager()
        self.content_generator = ContentGenerator(model, ollama_url)
        
    def generate_all(self, output_path: str, industry: str, role: Optional[str] = None,
                    language: str = "en") -> bool:
        """
        Generate complete folder structure with files.
        
        Args:
            output_path: Base output path
            industry: Industry context
            role: Specific role within the industry (optional)
            language: Language to use
            
        Returns:
            True if successful, False otherwise
        """
        # Check if we're operating in an existing directory with metadata
        base_dir = Path(output_path)
        if self.file_manager.file_exists(str(base_dir / ".metadata.json")):
            metadata = self.file_manager.read_json_file(str(base_dir / ".metadata.json"))
            if metadata:
                # Update industry/role from metadata if not explicitly provided
                if not industry and "industry" in metadata:
                    industry = metadata["industry"]
                    logging.info(f"Using industry '{industry}' from metadata")
                
                if role is None and "role" in metadata:
                    role = metadata["role"]
                    logging.info(f"Using role '{role}' from metadata")
                
                # Work directly in the current directory
                target_dir = base_dir
            else:
                # Create formatted directory name
                formatted_dir_name = f"{industry}_{role if role else 'general'}"
                formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
                target_dir = base_dir / formatted_dir_name
        else:
            # Create formatted directory name
            formatted_dir_name = f"{industry}_{role if role else 'general'}"
            formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
            target_dir = base_dir / formatted_dir_name
        
        # Ensure we have industry information
        if not industry:
            logging.error("Industry information is required but was not found in metadata or arguments")
            return False
            
        # Create target directory if it doesn't exist
        if not self.file_manager.ensure_directory(str(target_dir)):
            return False
            
        # Generate level 1 folder structure
        level1_structure = self._generate_level1_folders(industry, language, role)
        if not level1_structure or "folders" not in level1_structure:
            logging.error("Failed to generate valid level 1 folder structure")
            return False
            
        # Process folder structure (creates folders and files)
        return self._process_folder_structure(level1_structure, target_dir, industry, language, role)
    
    def generate_structure_only(self, output_path: str, industry: str, role: Optional[str] = None,
                               language: str = "en") -> bool:
        """
        Generate folder structure only without files.
        
        Args:
            output_path: Base output path
            industry: Industry context
            role: Specific role within the industry (optional)
            language: Language to use
            
        Returns:
            True if successful, False otherwise
        """
        # Check if we're operating in an existing directory with metadata
        base_dir = Path(output_path)
        if self.file_manager.file_exists(str(base_dir / ".metadata.json")):
            metadata = self.file_manager.read_json_file(str(base_dir / ".metadata.json"))
            if metadata:
                # Update industry/role from metadata if not explicitly provided
                if not industry and "industry" in metadata:
                    industry = metadata["industry"]
                    logging.info(f"Using industry '{industry}' from metadata")
                
                if role is None and "role" in metadata:
                    role = metadata["role"]
                    logging.info(f"Using role '{role}' from metadata")
                
                # Work directly in the current directory
                target_dir = base_dir
            else:
                # Create formatted directory name
                formatted_dir_name = f"{industry}_{role if role else 'general'}"
                formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
                target_dir = base_dir / formatted_dir_name
        else:
            # Create formatted directory name
            formatted_dir_name = f"{industry}_{role if role else 'general'}"
            formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
            target_dir = base_dir / formatted_dir_name
            
        # Ensure we have industry information
        if not industry:
            logging.error("Industry information is required but was not found in metadata or arguments")
            return False
        
        # Create target directory if it doesn't exist
        if not self.file_manager.ensure_directory(str(target_dir)):
            return False
            
        # Generate level 1 folder structure
        level1_structure = self._generate_level1_folders(industry, language, role)
        if not level1_structure or "folders" not in level1_structure:
            logging.error("Failed to generate valid level 1 folder structure")
            return False
            
        # Process folder structure (creates folders only)
        return self._process_structure_only(level1_structure, target_dir, industry, language, role)
    
    def _process_structure_only(self, level1_structure: Dict[str, Any], target_dir: Path,
                               industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Process and create the folder structure without generating files.
        
        Args:
            level1_structure: Level 1 folder structure data
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        level1_folders = list(level1_structure["folders"].keys())
        success = True
        
        # Store root level metadata
        root_metadata = {
            "industry": industry,
            "language": language,
            "role": role,
            "folders": level1_structure["folders"]
        }
        self.file_manager.write_json_file(str(target_dir / ".metadata.json"), root_metadata)
        
        for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
            if not isinstance(l1_folder_data, dict) or "description" not in l1_folder_data:
                logging.warning(f"Invalid data for folder {l1_folder_name}, skipping")
                continue
                
            # Create level 1 folder
            l1_folder_path = target_dir / self.file_manager.sanitize_path(l1_folder_name)
            if not self.file_manager.ensure_directory(str(l1_folder_path)):
                success = False
                continue
                
            logging.info(f"Created level 1 folder: {l1_folder_name}")
            
            # Store level 1 folder metadata
            l1_metadata = {
                "name": l1_folder_name,
                "description": l1_folder_data.get("description", ""),
                "industry": industry,
                "purpose": l1_folder_data.get("purpose")
            }
            self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
            
            # Generate level 2 folder structure
            level2_structure = self._generate_level2_folders(
                industry, l1_folder_name, l1_folder_data.get("description", ""), language, role
            )
            
            if not level2_structure or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping")
                continue
            
            # Add folders to level 1 metadata
            l1_metadata["folders"] = level2_structure["folders"]
            self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
            
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
                    
                logging.info(f"Created level 2 folder: {l1_folder_name}/{l2_folder_name}")
                
                # Store level 2 folder metadata
                l2_metadata = {
                    "name": l2_folder_name,
                    "description": l2_folder_data.get("description", ""),
                    "parent_folder": l1_folder_name,
                    "industry": industry,
                    "purpose": l2_folder_data.get("purpose")
                }
                self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                
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
                
                # Process level 3 folders
                for l3_folder_name, l3_folder_data in level3_structure["folders"].items():
                    if not isinstance(l3_folder_data, dict) or "description" not in l3_folder_data:
                        logging.warning(f"Invalid data for level 3 folder {l3_folder_name}, skipping")
                        continue
                        
                    # Create level 3 folder
                    l3_folder_path = l2_folder_path / self.file_manager.sanitize_path(l3_folder_name)
                    if not self.file_manager.ensure_directory(str(l3_folder_path)):
                        success = False
                        continue
                        
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
        
        logging.info("Folder structure creation completed")
        return success
    
    def generate_files_only(self, output_path: str, industry: str, role: Optional[str] = None,
                          language: str = "en") -> bool:
        """
        Generate or update files only without modifying folder structure.
        
        Args:
            output_path: Base output path
            industry: Industry context (can be None if metadata exists)
            role: Specific role within the industry (optional)
            language: Language to use
            
        Returns:
            True if successful, False otherwise
        """
        # Set target directory
        base_dir = Path(output_path)
        
        # Try to determine directory name from metadata if present
        if self.file_manager.file_exists(str(base_dir / ".metadata.json")):
            metadata = self.file_manager.read_json_file(str(base_dir / ".metadata.json"))
            if metadata:
                # Update industry/role from metadata if not explicitly provided
                if not industry and "industry" in metadata:
                    industry = metadata["industry"]
                    logging.info(f"Using industry '{industry}' from metadata")
                
                if role is None and "role" in metadata:
                    role = metadata["role"]
                    logging.info(f"Using role '{role}' from metadata")
                
                # Work directly in the current directory
                target_dir = base_dir
            else:
                # No metadata found, so create formatted directory
                formatted_dir_name = f"{industry}_{role if role else 'general'}"
                formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
                target_dir = base_dir / formatted_dir_name
        else:
            # No metadata found, so create formatted directory
            formatted_dir_name = f"{industry}_{role if role else 'general'}"
            formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
            target_dir = base_dir / formatted_dir_name
        
        # Ensure we have industry information
        if not industry:
            logging.error("Industry information is required but was not found in metadata or arguments")
            return False
        
        # Check if target directory exists
        if not target_dir.exists():
            logging.error(f"Target directory {target_dir} does not exist. Run 'all' command first.")
            return False
            
        # Traverse existing folder structure and regenerate files
        return self._regenerate_files(target_dir, industry, language, role)
    
    def _generate_level1_folders(self, industry: str, language: str, 
                               role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate level 1 folder structure.
        
        Args:
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Dictionary with folder structure information
        """
        prompt = self._get_level1_folders_prompt(industry, language, role)
        
        return self.llm_client.get_json_completion(
            prompt=prompt,
            structure_hint="The JSON should have a structure with a 'folders' key containing objects",
            max_attempts=3
        )
    
    def _process_folder_structure(self, level1_structure: Dict[str, Any], target_dir: Path,
                                industry: str, language: str, role: Optional[str] = None) -> bool:
        """
        Process and create the folder structure.
        
        Args:
            level1_structure: Level 1 folder structure data
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        level1_folders = list(level1_structure["folders"].keys())
        success = True
        
        # Store root level metadata
        root_metadata = {
            "industry": industry,
            "language": language,
            "role": role,
            "folders": level1_structure["folders"]
        }
        self.file_manager.write_json_file(str(target_dir / ".metadata.json"), root_metadata)
        
        # Track timeseries folders at level 1
        if self.content_generator.is_timeseries_limit_reached(str(target_dir)):
            logging.warning("Maximum number of timeseries folders at level 1 reached")
        
        for l1_folder_name, l1_folder_data in level1_structure["folders"].items():
            if not isinstance(l1_folder_data, dict) or "description" not in l1_folder_data:
                logging.warning(f"Invalid data for folder {l1_folder_name}, skipping")
                continue
                
            # Create level 1 folder
            l1_folder_path = target_dir / self.file_manager.sanitize_path(l1_folder_name)
            if not self.file_manager.ensure_directory(str(l1_folder_path)):
                success = False
                continue
                
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
                
                # Generate timeseries files for this folder
                self._generate_timeseries_files(
                    l1_folder_path, l1_folder_name, l1_folder_data.get("description", ""),
                    industry, language, role
                )
                continue
            
            # Generate level 2 folder structure
            level2_structure = self._generate_level2_folders(
                industry, l1_folder_name, l1_folder_data.get("description", ""), language, role
            )
            
            if not level2_structure or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping")
                continue
            
            # Add folders to level 1 metadata
            l1_metadata["folders"] = level2_structure["folders"]
            self.file_manager.write_json_file(str(l1_folder_path / ".metadata.json"), l1_metadata)
            
            # Track timeseries folders at level 2
            if self.content_generator.is_timeseries_limit_reached(str(l1_folder_path)):
                logging.warning(f"Maximum number of timeseries folders in {l1_folder_name} reached")
                
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
                    self._generate_timeseries_files(
                        l2_folder_path, l2_folder_name, l2_folder_data.get("description", ""),
                        industry, language, role
                    )
                    continue
                
                # Generate level 3 folder structure
                level3_structure = self._generate_level3_folders(
                    industry, l2_folder_name, l2_folder_data, 
                    l1_folder_data.get("description", ""), l1_folder_name, language, role
                )
                
                if not level3_structure or "folders" not in level3_structure:
                    logging.warning(f"Failed to get valid level 3 structure for {l1_folder_name}/{l2_folder_name}, skipping")
                    continue
                
                # Generate files for level 2 folder
                level3_files = self._generate_level3_files(
                    industry, l2_folder_name, l2_folder_data,
                    l1_folder_data.get("description", ""), l1_folder_name, language, role
                )
                
                # Add folders and files to level 2 metadata
                l2_metadata["folders"] = level3_structure["folders"]
                
                # Add files to metadata if available
                if "files" in level3_files and isinstance(level3_files["files"], list):
                    l2_metadata["files"] = level3_files["files"]
                
                self.file_manager.write_json_file(str(l2_folder_path / ".metadata.json"), l2_metadata)
                
                # Track timeseries folders at level 3
                if self.content_generator.is_timeseries_limit_reached(str(l2_folder_path)):
                    logging.warning(f"Maximum number of timeseries folders in {l1_folder_name}/{l2_folder_name} reached")
                
                # Create level 3 folders
                for l3_folder_name, l3_folder_data in level3_structure["folders"].items():
                    if not isinstance(l3_folder_data, dict) or "description" not in l3_folder_data:
                        logging.warning(f"Invalid data for level 3 folder {l3_folder_name}, skipping")
                        continue
                        
                    # Create level 3 folder
                    l3_folder_path = l2_folder_path / self.file_manager.sanitize_path(l3_folder_name)
                    if not self.file_manager.ensure_directory(str(l3_folder_path)):
                        success = False
                        continue
                        
                    logging.info(f"Created level 3 folder: {l1_folder_name}/{l2_folder_name}/{l3_folder_name}")
                    
                    # Get folder purpose if specified
                    l3_folder_purpose = l3_folder_data.get("purpose")
                    
                    # Store level 3 folder metadata
                    l3_metadata = {
                        "name": l3_folder_name,
                        "description": l3_folder_data.get("description", ""),
                        "parent_folder": l2_folder_name,
                        "grandparent_folder": l1_folder_name,
                        "industry": industry,
                        "purpose": l3_folder_purpose
                    }
                    self.file_manager.write_json_file(str(l3_folder_path / ".metadata.json"), l3_metadata)
                    
                    # Generate timeseries files for timeseries folders
                    if l3_folder_purpose == "timeseries":
                        logging.info(f"Folder {l1_folder_name}/{l2_folder_name}/{l3_folder_name} is marked as timeseries")
                        self._generate_timeseries_files(
                            l3_folder_path, l3_folder_name, l3_folder_data.get("description", ""),
                            industry, language, role
                        )
                
                # Generate files for level 2 folder
                if "files" in level3_files and isinstance(level3_files["files"], list):
                    logging.info(f"Creating {len(level3_files['files'])} files in {l1_folder_name}/{l2_folder_name}")
                    
                    # Create each file
                    for file_info in level3_files["files"]:
                        try:
                            if not isinstance(file_info, dict) or "name" not in file_info:
                                continue
                                
                            file_name = file_info["name"]
                            file_description = file_info.get("description", "")
                            
                            self.content_generator.generate_file(
                                str(l2_folder_path), file_name, file_description,
                                industry, language, role, l2_folder_purpose
                            )
                            logging.info(f"Created file: {l1_folder_name}/{l2_folder_name}/{file_name}")
                        except Exception as e:
                            logging.error(f"Error creating file: {e}")
                            success = False
        
        return success
    
    def _regenerate_files(self, target_dir: Path, industry: str, language: str, 
                        role: Optional[str] = None) -> bool:
        """
        Regenerate files in an existing folder structure.
        
        Args:
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        for level1_item in target_dir.iterdir():
            # Skip non-directories and metadata
            if not level1_item.is_dir() or level1_item.name.startswith('.'):
                continue
                
            # Check for metadata file
            l1_metadata_path = level1_item / ".metadata.json"
            if not l1_metadata_path.exists():
                logging.warning(f"No metadata found for {level1_item}, skipping")
                continue
                
            # Load metadata
            l1_metadata = self.file_manager.read_json_file(str(l1_metadata_path))
            if not l1_metadata:
                logging.warning(f"Failed to read metadata for {level1_item}, skipping")
                continue
                
            # Check if this is a timeseries folder
            if l1_metadata.get("purpose") == "timeseries":
                # Regenerate timeseries files for this folder
                folder_name = l1_metadata.get("name", level1_item.name)
                folder_desc = l1_metadata.get("description", "")
                self._generate_timeseries_files(
                    level1_item, folder_name, folder_desc,
                    industry, language, role
                )
                continue
                
            # Skip if no subfolders
            if not "folders" in l1_metadata or not isinstance(l1_metadata["folders"], dict):
                continue
                
            # Process level 2 folders
            for level2_item in level1_item.iterdir():
                # Skip non-directories and metadata
                if not level2_item.is_dir() or level2_item.name.startswith('.'):
                    continue
                    
                # Check for metadata file
                l2_metadata_path = level2_item / ".metadata.json"
                if not l2_metadata_path.exists():
                    logging.warning(f"No metadata found for {level2_item}, skipping")
                    continue
                    
                # Load metadata
                l2_metadata = self.file_manager.read_json_file(str(l2_metadata_path))
                if not l2_metadata:
                    logging.warning(f"Failed to read metadata for {level2_item}, skipping")
                    continue
                    
                # Check if this is a timeseries folder
                if l2_metadata.get("purpose") == "timeseries":
                    # Regenerate timeseries files for this folder
                    folder_name = l2_metadata.get("name", level2_item.name)
                    folder_desc = l2_metadata.get("description", "")
                    self._generate_timeseries_files(
                        level2_item, folder_name, folder_desc,
                        industry, language, role
                    )
                    continue
                
                # Generate files for level 2 folder based on existing metadata
                l2_folder_name = l2_metadata.get("name", level2_item.name)
                l2_description = l2_metadata.get("description", "")
                l1_folder_name = l2_metadata.get("parent_folder", level1_item.name)
                l1_description = l1_metadata.get("description", "")
                l2_purpose = l2_metadata.get("purpose")
                
                # Find or generate level 2 folder files
                if "files" in l2_metadata and isinstance(l2_metadata["files"], list):
                    # Use existing file definitions
                    for file_info in l2_metadata["files"]:
                        if not isinstance(file_info, dict) or "name" not in file_info:
                            continue
                            
                        file_name = file_info["name"]
                        file_description = file_info.get("description", "")
                        
                        self.content_generator.generate_file(
                            str(level2_item), file_name, file_description,
                            industry, language, role, l2_purpose
                        )
                        logging.info(f"Regenerated file: {level1_item.name}/{level2_item.name}/{file_name}")
                else:
                    # Generate new file definitions
                    level3_files = self._generate_level3_files(
                        industry, l2_folder_name, {"description": l2_description},
                        l1_description, l1_folder_name, language, role
                    )
                    
                    if "files" in level3_files and isinstance(level3_files["files"], list):
                        # Add files to metadata
                        l2_metadata["files"] = level3_files["files"]
                        self.file_manager.write_json_file(str(l2_metadata_path), l2_metadata)
                        
                        # Create each file
                        for file_info in level3_files["files"]:
                            if not isinstance(file_info, dict) or "name" not in file_info:
                                continue
                                
                            file_name = file_info["name"]
                            file_description = file_info.get("description", "")
                            
                            self.content_generator.generate_file(
                                str(level2_item), file_name, file_description,
                                industry, language, role, l2_purpose
                            )
                            logging.info(f"Generated file: {level1_item.name}/{level2_item.name}/{file_name}")
                
                # Process level 3 folders
                if "folders" in l2_metadata and isinstance(l2_metadata["folders"], dict):
                    for level3_item in level2_item.iterdir():
                        # Skip non-directories and metadata
                        if not level3_item.is_dir() or level3_item.name.startswith('.'):
                            continue
                            
                        # Check for metadata file
                        l3_metadata_path = level3_item / ".metadata.json"
                        if not l3_metadata_path.exists():
                            logging.warning(f"No metadata found for {level3_item}, skipping")
                            continue
                            
                        # Load metadata
                        l3_metadata = self.file_manager.read_json_file(str(l3_metadata_path))
                        if not l3_metadata:
                            logging.warning(f"Failed to read metadata for {level3_item}, skipping")
                            continue
                            
                        # Check if this is a timeseries folder
                        if l3_metadata.get("purpose") == "timeseries":
                            # Regenerate timeseries files for this folder
                            folder_name = l3_metadata.get("name", level3_item.name)
                            folder_desc = l3_metadata.get("description", "")
                            self._generate_timeseries_files(
                                level3_item, folder_name, folder_desc,
                                industry, language, role
                            )
                            continue
                        
                        # Generate files for level 3 folder (if needed in the future)
                        # Currently not implemented
        
        return success
    
    def _get_level1_folders_prompt(self, industry: str, language: str, role: Optional[str] = None) -> str:
        """
        Get prompt for level 1 folder generation.
        
        Args:
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Prompt string
        """
        role_context = f" for a {role}" if role else ""
        
        return (
            f"You are an expert in {industry} documentation{role_context}. "
            f"Create a logical top-level folder structure for {industry} documentation{role_context}. "
            f"Create between 3-7 top-level folders that would contain all necessary documentation. "
            f"For each folder, provide a brief description of what it would contain. "
            f"If a folder is meant to contain regular reports or logs that would be created on a daily, weekly, "
            f"or monthly basis (like performance reports, sales logs, etc.), mark it with purpose 'timeseries'. "
            f"Note that folders with purpose 'timeseries' will not contain subfolders, only regularly updated files. "
            f"Limit the number of timeseries folders to ensure they are only used when truly appropriate. "
            f"The folder names and descriptions should be in {language} language. "
            f"Return the response as a JSON object with the following structure: "
            "{\n"
            '  "folders": {\n'
            '    "folder1": {\n'
            '      "description": "Description of folder1",\n'
            '      "purpose": "general"\n'
            '    },\n'
            '    "timeseries_folder": {\n'
            '      "description": "Regular daily reports",\n'
            '      "purpose": "timeseries"\n'
            '    },\n'
            '    ...\n'
            '  }\n'
            "}"
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
            structure_hint="The JSON should have a structure with a 'folders' key containing objects",
            max_attempts=3
        )
    
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
        """
        role_context = f" for a {role}" if role else ""
        
        return (
            f"You are an expert in {industry} documentation{role_context}. "
            f"Create a logical folder structure for the '{l1_folder_name}' folder, which contains: {l1_description}. "
            f"Create between 2-5 subfolders that would contain all necessary documentation for this area. "
            f"For each folder, provide a brief description of what it would contain. "
            f"If a folder is meant to contain regular reports or logs that would be created on a daily, weekly, "
            f"or monthly basis (like performance reports, sales logs, etc.), mark it with purpose 'timeseries'. "
            f"Note that folders with purpose 'timeseries' will not contain subfolders, only regularly updated files. "
            f"Limit the number of timeseries folders to ensure they are only used when truly appropriate. "
            f"The folder names and descriptions should be in {language} language. "
            f"Return the response as a JSON object with the following structure: "
            "{\n"
            '  "folders": {\n'
            '    "folder1": {\n'
            '      "description": "Description of folder1",\n'
            '      "purpose": "general"\n'
            '    },\n'
            '    "timeseries_folder": {\n'
            '      "description": "Regular weekly reports",\n'
            '      "purpose": "timeseries"\n'
            '    },\n'
            '    ...\n'
            '  }\n'
            "}"
        )
    
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
            structure_hint="The JSON should have a structure with a 'folders' key containing objects",
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
        """
        role_context = f" for a {role}" if role else ""
        l2_description = l2_folder_data.get("description", "")
        
        return (
            f"You are an expert in {industry} documentation{role_context}. "
            f"Create a logical folder structure for the '{l2_folder_name}' folder, which is within '{l1_folder_name}' "
            f"({l1_description}) and contains: {l2_description}. "
            f"Create between 0-3 subfolders that would contain specific documentation for this area. "
            f"For each folder, provide a brief description of what it would contain. "
            f"If a folder is meant to contain regular reports or logs that would be created on a daily, weekly, "
            f"or monthly basis (like performance reports, sales logs, etc.), mark it with purpose 'timeseries'. "
            f"Note that folders with purpose 'timeseries' will not contain subfolders, only regularly updated files. "
            f"Limit the number of timeseries folders to ensure they are only used when truly appropriate. "
            f"The folder names and descriptions should be in {language} language. "
            f"Return the response as a JSON object with the following structure: "
            "{\n"
            '  "folders": {\n'
            '    "folder1": {\n'
            '      "description": "Description of folder1",\n'
            '      "purpose": "general"\n'
            '    },\n'
            '    "timeseries_folder": {\n'
            '      "description": "Regular monthly reports",\n'
            '      "purpose": "timeseries"\n'
            '    },\n'
            '    ...\n'
            '  }\n'
            "}"
        )
    
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
            structure_hint="The JSON should have a structure with a 'files' key containing an array of objects",
            max_attempts=3
        )
    
    def _get_level3_files_prompt(self, industry: str, l2_folder_name: str, 
                               l2_folder_data: Dict[str, Any], l1_description: str,
                               l1_folder_name: str, language: str, 
                               role: Optional[str] = None) -> str:
        """
        Get prompt for generating level 3 files.
        
        Args:
            industry: Industry context
            l2_folder_name: Level 2 folder name
            l2_folder_data: Level 2 folder data
            l1_description: Level 1 folder description
            l1_folder_name: Level 1 folder name
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Formatted prompt
        """
        role_context = f" for a {role}" if role else ""
        l2_description = l2_folder_data.get("description", "")
        
        return (
            f"For a {industry} industry{role_context}, create a list of files for the '{l2_folder_name}' "
            f"subfolder which is inside the '{l1_folder_name}' folder. "
            f"The '{l1_folder_name}' folder is described as: '{l1_description}'. "
            f"The '{l2_folder_name}' subfolder is described as: '{l2_description}'. "
            f"Include a mix of document types (txt, docx, pdf, xlsx, images). "
            f"The files should be in {language} language. "
            f"For each file, provide a name and a brief description of its content."
        )
    
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
        """
        prompt = f"""
        Generate 5 example files that would typically be found in a timeseries folder named '{folder_name}' 
        with the description '{folder_description}' for the {industry} industry.
        
        These files should represent regular reports or logs that would be created on a daily, weekly, 
        or monthly basis.
        
        Return the response as a JSON object with the following structure:
        {{
            "files": [
                {{
                    "name": "example1.txt",
                    "description": "Description of example1"
                }},
                ...
            ]
        }}
        """
        
        file_structure = self.llm_client.get_json_completion(
            prompt=prompt,
            structure_hint="The JSON should have a 'files' key containing an array of file objects",
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
            except Exception as e:
                logging.error(f"Error creating timeseries file: {e}")
                success = False
                
        return success 