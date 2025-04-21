#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", output_path: str = ".") -> None:
    """Configure logging settings"""
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
    
    # File handler for logging to a file in the output path
    output_dir = Path(output_path)
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(exist_ok=True, parents=True)
    log_file = logs_dir / f"sharinbai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logging.info(f"=== Sharinbai Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log file: {log_file}") 