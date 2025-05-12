"""
Factory for creating LLM clients
"""

import logging
from typing import Optional

from src.config.settings import Settings
from src.foundation.llm_base import LLMClient
from src.foundation.llm_client import OllamaClient
from src.foundation.openai_client import OpenAIClient

def create_llm_client(settings: Settings) -> LLMClient:
    """
    Create an LLM client based on the provider setting
    
    Args:
        settings: Application settings
        
    Returns:
        An LLM client instance
    
    Raises:
        ValueError: If the provider is not supported
    """
    if settings.provider == Settings.PROVIDER_OLLAMA:
        return OllamaClient(model=settings.model, ollama_url=settings.ollama_url)
    elif settings.provider == Settings.PROVIDER_OPENAI:
        return OpenAIClient(
            model=settings.model,
            api_key=settings.openai_api_key,
            api_base=settings.openai_api_base,
            organization=settings.openai_organization
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.provider}")
