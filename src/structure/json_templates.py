"""
JSON Templates for Folder Structure Generation

This module provides JSON structure templates that were previously embedded in language resource files.
By separating these templates from the translated content, we improve the readability and maintainability
of the language resources.
"""

from typing import Dict, Any


class JsonTemplates:
    """
    Contains JSON templates for different structures used in folder generation.
    
    These templates were previously embedded within language resource files,
    but are now separated to improve the readability of language resources and
    to centralize the JSON structure definitions.
    """
    
    # Templates for level 1 folder structure
    LEVEL1_FOLDERS_TEMPLATE = """
{{
  "folders": {{
    "FolderName1": {{
      "description": "{folder_description}"
    }},
    "FolderName2": {{
      "description": "{folder_description}"
    }}
  }}
}}
"""

    # Templates for level 2 folder structure
    LEVEL2_FOLDERS_TEMPLATE = """
{{
  "folders": {{
    "FolderName1": {{
      "description": "{folder_description}"
    }},
    "FolderName2": {{
      "description": "{folder_description}"
    }}
  }}
}}
"""

    # Templates for level 3 folder structure
    LEVEL3_FOLDERS_TEMPLATE = """
{{
  "folders": {{
    "FolderName1": {{
      "description": "{folder_description}"
    }},
    "FolderName2": {{
      "description": "{folder_description}"
    }}
  }}
}}
"""

    # Templates for level 3 files structure
    LEVEL3_FILES_TEMPLATE = """
{{
  "files": [
    {{
      "name": "FileName1.extension",
      "type": "docx|xlsx|pdf|txt|png|jpg",
      "description": "{file_description}"
    }},
    {{
      "name": "FileName2.extension",
      "type": "docx|xlsx|pdf|txt|png|jpg",
      "description": "{file_description}"
    }}
  ]
}}
"""

    # Templates for the complete folder structure
    COMPLETE_STRUCTURE_TEMPLATE = """
{{
    "Folder Name": {{
        "folders": {{
            "Subfolder Name": {{
                "files": [
                    {{"name": "filename.extension", "type": "docx|xlsx|pdf|txt|png|jpg", "description": "{file_description}"}}
                ],
                "folders": {{}}
            }}
        }},
        "files": [
            {{"name": "filename.extension", "type": "docx|xlsx|pdf|txt|png|jpg", "description": "{file_description}"}}
        ]
    }}
}}
"""

    @classmethod
    def get_template(cls, template_name: str) -> str:
        """
        Get a specific JSON template by name.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            The template string or empty string if template not found
        """
        template_mapping = {
            'level1_folders': cls.LEVEL1_FOLDERS_TEMPLATE,
            'level2_folders': cls.LEVEL2_FOLDERS_TEMPLATE,
            'level3_folders': cls.LEVEL3_FOLDERS_TEMPLATE,
            'level3_files': cls.LEVEL3_FILES_TEMPLATE,
            'complete_structure': cls.COMPLETE_STRUCTURE_TEMPLATE
        }
        
        return template_mapping.get(template_name, "") 