"""
Logging configuration module
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", output_path: str = ".", log_path: str = "./logs") -> None:
    """
    Configure logging settings.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output_path: Base path for output files
        log_path: Path for log files (default: ./logs)
    """
    # Logger configuration
    # Set root logger level to DEBUG to capture everything
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Determine console level based on input, default to INFO
    console_level_str = log_level.upper()
    try:
        console_level = getattr(logging, console_level_str)
        # Ensure it's a valid level integer
        if not isinstance(console_level, int):
            raise AttributeError
    except AttributeError:
        logging.warning(f"Invalid log level '{log_level}'. Defaulting console to INFO.")
        console_level_str = "INFO"
        console_level = logging.INFO
        
    # Remove all existing handlers to prevent duplicate output
    # It's crucial to do this after getting the logger and before adding new handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Console handler (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)  # Use determined console level
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # Add console handler first
    logger.addHandler(console_handler)
    
    try:
        # Use the designated logs directory
        logs_dir = Path(log_path)
        logs_dir.mkdir(exist_ok=True, parents=True)
        
        # File handler for logging to a file
        log_file = logs_dir / f"sharinbai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        # Set file handler level to DEBUG unconditionally
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Added logger name
        file_handler.setFormatter(file_format)
        
        # Add file handler
        logger.addHandler(file_handler)
        
        logging.info(f"=== Sharinbai Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        # Log the *effective* console level and file level
        logging.info(f"Console log level: {console_level_str}")
        logging.info(f"File log level: DEBUG") 
        logging.info(f"Log file: {log_file}")
    except Exception as e:
        logging.error(f"Failed to set up log file in {log_path}: {e}")
        logging.warning("Continuing with console logging only") 