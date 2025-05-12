"""
Settings module for application configuration
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

class Settings:
    """Application settings and configuration"""
    
    # Default model names
    DEFAULT_OLLAMA_MODEL = "gemma3:4b"
    DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"
    
    # LLM provider types
    PROVIDER_OLLAMA = "ollama"
    PROVIDER_OPENAI = "openai"
    
    # Default provider
    DEFAULT_PROVIDER = PROVIDER_OLLAMA
    
    def __init__(self):
        """Initialize default settings"""
        # Default LLM provider
        self.provider = self.DEFAULT_PROVIDER
        
        # Default model
        self.model = self.DEFAULT_OLLAMA_MODEL
        
        # Default output path
        self.output_path = os.path.abspath("./out")
        
        # Default log path
        self.log_path = os.path.abspath("./logs")
        
        # Default language
        self.language = None
        
        # Default log level
        self.log_level = "INFO"
        
        # Ollama-specific settings
        self.ollama_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
        
        # OpenAI-specific settings
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.openai_api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.openai_organization = os.environ.get("OPENAI_ORGANIZATION")
        
        # Initialize industry and role with None
        self.industry = None
        self.role = None
        
    def from_args(self, args: Dict[str, Any]) -> 'Settings':
        """
        Update settings from command line arguments.
        
        Args:
            args: Dictionary of argument values
            
        Returns:
            Self for chaining
        """
        # Update settings from args
        if args.get('provider'):
            self.provider = args['provider']
            
        if args.get('model'):
            self.model = args['model']
            
        if args.get('path'):
            self.output_path = os.path.abspath(args['path'])
            
        if args.get('log_path'):
            self.log_path = os.path.abspath(args['log_path'])
            
        if args.get('language'):
            self.language = args['language']
            
        if args.get('log_level'):
            self.log_level = args['log_level']
            
        # Ollama-specific settings
        if args.get('ollama_url'):
            self.ollama_url = args['ollama_url']
            
        # OpenAI-specific settings
        if args.get('openai_api_key'):
            self.openai_api_key = args['openai_api_key']
            
        if args.get('openai_api_base'):
            self.openai_api_base = args['openai_api_base']
            
        if args.get('openai_organization'):
            self.openai_organization = args['openai_organization']
            
        if args.get('industry'):
            self.industry = args['industry']
            
        if args.get('role'):
            self.role = args['role']
            
        return self 