"""
Settings module for application configuration
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

class Settings:
    """Application settings and configuration"""
    
    def __init__(self):
        """Initialize default settings"""
        # Default model
        self.model = "llama3"
        
        # Default output path
        self.output_path = os.path.abspath("./out")
        
        # Default language
        self.language = "en"
        
        # Default log level
        self.log_level = "INFO"
        
        # Default Ollama API URL
        self.ollama_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
        
    def from_args(self, args: Dict[str, Any]) -> 'Settings':
        """
        Update settings from command line arguments.
        
        Args:
            args: Dictionary of argument values
            
        Returns:
            Self for chaining
        """
        # Update settings from args
        if args.get('model'):
            self.model = args['model']
            
        if args.get('path'):
            self.output_path = os.path.abspath(args['path'])
            
        if args.get('language'):
            self.language = args['language']
            
        if args.get('log_level'):
            self.log_level = args['log_level']
            
        if args.get('ollama_url'):
            self.ollama_url = args['ollama_url']
            
        if args.get('industry'):
            self.industry = args['industry']
            
        if args.get('role'):
            self.role = args['role']
            
        return self 