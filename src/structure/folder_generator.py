"""
Folder structure generator
"""

import logging
import os
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
        # Create formatted directory name
        formatted_dir_name = f"{industry}_{role if role else 'general'}"
        formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
        
        # Set target directory
        base_dir = Path(output_path)
        target_dir = base_dir / formatted_dir_name
        
        # Create root directory
        if not self.file_manager.ensure_directory(str(target_dir)):
            return False
            
        # Generate level 1 folder structure
        level1_structure = self._generate_level1_folders(industry, language, role)
        if not level1_structure or "folders" not in level1_structure:
            logging.error("Failed to get valid level 1 folder structure")
            return False
            
        # Create level 1 folders and process level 2 and 3
        return self._process_folder_structure(level1_structure, target_dir, industry, language, role)
    
    def generate_files_only(self, output_path: str, industry: str, role: Optional[str] = None,
                          language: str = "en") -> bool:
        """
        Generate or update files only without modifying folder structure.
        
        Args:
            output_path: Base output path
            industry: Industry context
            role: Specific role within the industry (optional)
            language: Language to use
            
        Returns:
            True if successful, False otherwise
        """
        # Create formatted directory name
        formatted_dir_name = f"{industry}_{role if role else 'general'}"
        formatted_dir_name = self.file_manager.sanitize_path(formatted_dir_name)
        
        # Set target directory
        base_dir = Path(output_path)
        target_dir = base_dir / formatted_dir_name
        
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
            
            # Generate level 2 folder structure
            level2_structure = self._generate_level2_folders(
                industry, l1_folder_name, l1_folder_data.get("description", ""), language, role
            )
            
            if not level2_structure or "folders" not in level2_structure:
                logging.error(f"Failed to get valid level 2 structure for {l1_folder_name}, skipping")
                continue
                
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
                
                # Generate level 3 folder structure
                level3_structure = self._generate_level3_folders(
                    industry, l2_folder_name, l2_folder_data, 
                    l1_folder_data.get("description", ""), l1_folder_name, language, role
                )
                
                if not level3_structure or "folders" not in level3_structure:
                    logging.warning(f"Failed to get valid level 3 structure for {l1_folder_name}/{l2_folder_name}, skipping")
                    continue
                
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
                
                # Generate files for level 2 folder
                level3_files = self._generate_level3_files(
                    industry, l2_folder_name, l2_folder_data,
                    l1_folder_data.get("description", ""), l1_folder_name, language, role
                )
                
                if "files" in level3_files and isinstance(level3_files["files"], list):
                    logging.info(f"Creating {len(level3_files['files'])} files in {l1_folder_name}/{l2_folder_name}")
                    
                    # Create each file
                    for file_info in level3_files["files"]:
                        try:
                            if not isinstance(file_info, dict) or "name" not in file_info:
                                continue
                                
                            filename = file_info["name"]
                            description = file_info.get("description", "")
                            
                            # Generate file content
                            file_success = self.content_generator.generate_file(
                                str(l2_folder_path),
                                filename,
                                description,
                                industry,
                                language,
                                role
                            )
                            
                            if file_success:
                                logging.info(f"Created file: {l1_folder_name}/{l2_folder_name}/{filename}")
                            else:
                                success = False
                        except Exception as e:
                            logging.error(f"Error creating file {file_info.get('name', 'unknown')}: {e}")
                            success = False
        
        return success
    
    def _regenerate_files(self, target_dir: Path, industry: str, language: str, 
                        role: Optional[str] = None) -> bool:
        """
        Regenerate all files in the existing folder structure.
        
        Args:
            target_dir: Target directory
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        # Traverse level 1 folders
        for l1_folder_path in target_dir.iterdir():
            if not l1_folder_path.is_dir():
                continue
                
            # Traverse level 2 folders
            for l2_folder_path in l1_folder_path.iterdir():
                if not l2_folder_path.is_dir():
                    continue
                    
                # Get level 2 folder information
                l1_folder_name = l1_folder_path.name
                l2_folder_name = l2_folder_path.name
                
                # Generate files for level 2 folder
                level3_files = self._generate_level3_files(
                    industry, l2_folder_name, {"description": l2_folder_name},
                    l1_folder_name, l1_folder_name, language, role
                )
                
                if "files" in level3_files and isinstance(level3_files["files"], list):
                    logging.info(f"Creating/updating {len(level3_files['files'])} files in {l1_folder_name}/{l2_folder_name}")
                    
                    # Create each file
                    for file_info in level3_files["files"]:
                        try:
                            if not isinstance(file_info, dict) or "name" not in file_info:
                                continue
                                
                            filename = file_info["name"]
                            description = file_info.get("description", "")
                            
                            # Generate file content
                            file_success = self.content_generator.generate_file(
                                str(l2_folder_path),
                                filename,
                                description,
                                industry,
                                language,
                                role
                            )
                            
                            if file_success:
                                logging.info(f"Created/updated file: {l1_folder_name}/{l2_folder_name}/{filename}")
                            else:
                                success = False
                        except Exception as e:
                            logging.error(f"Error creating/updating file {file_info.get('name', 'unknown')}: {e}")
                            success = False
        
        return success
    
    def _get_level1_folders_prompt(self, industry: str, language: str, role: Optional[str] = None) -> str:
        """
        Get prompt for generating level 1 folders.
        
        Args:
            industry: Industry context
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Formatted prompt
        """
        role_context = f" for a {role}" if role else ""
        
        return (
            f"Create a high-level folder structure for a {industry} industry{role_context}. "
            f"The folders should be in {language} language and cover major categories like "
            f"documentation, resources, data, etc. "
            f"For each folder, provide a brief description of its purpose."
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
        Get prompt for generating level 2 folders.
        
        Args:
            industry: Industry context
            l1_folder_name: Level 1 folder name
            l1_description: Level 1 folder description
            language: Language to use
            role: Specific role within the industry (optional)
            
        Returns:
            Formatted prompt
        """
        role_context = f" for a {role}" if role else ""
        
        return (
            f"For a {industry} industry{role_context}, create a list of subfolders for the '{l1_folder_name}' folder. "
            f"The '{l1_folder_name}' folder is described as: '{l1_description}'. "
            f"The folders should be in {language} language. "
            f"For each subfolder, provide a brief description of its purpose."
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
        Get prompt for generating level 3 folders.
        
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
            f"For a {industry} industry{role_context}, create a list of subfolders for the '{l2_folder_name}' "
            f"subfolder which is inside the '{l1_folder_name}' folder. "
            f"The '{l1_folder_name}' folder is described as: '{l1_description}'. "
            f"The '{l2_folder_name}' subfolder is described as: '{l2_description}'. "
            f"The folders should be in {language} language. "
            f"For each subfolder, provide a brief description of its purpose."
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