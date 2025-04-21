"""
Logging configuration module
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(log_level: str = "INFO", output_path: str = ".") -> None:
    """
    Configure logging settings.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output_path: Base path for log files
    """
    # Logger configuration
    level = getattr(logging, log_level.upper())
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove all existing handlers to prevent duplicate output
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # Add console handler first to capture any early messages
    logger.addHandler(console_handler)
    
    try:
        # Ensure output directory exists before trying to create logs directory
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Create logs directory
        logs_dir = output_dir / "logs"
        logs_dir.mkdir(exist_ok=True, parents=True)
        
        # File handler for logging to a file
        log_file = logs_dir / f"sharinbai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # Add file handler
        logger.addHandler(file_handler)
        
        logging.info(f"=== Sharinbai Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        logging.info(f"Log level: {log_level}")
        logging.info(f"Log file: {log_file}")
    except Exception as e:
        logging.error(f"Failed to set up log file in {output_path}: {e}")
        logging.warning("Continuing with console logging only") 