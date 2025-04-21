"""
Statistics tracker for generated content
"""

import time
import logging
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional

from ..config.ui_constants import (
    STATS_HEADER,
    STATS_FOLDER_COUNT,
    STATS_FILE_COUNT,
    STATS_FILE_TYPES_HEADER,
    STATS_FILE_TYPE_ITEM,
    STATS_PROCESSING_TIMES_HEADER,
    STATS_PROCESSING_TIME_ITEM,
    STATS_TOTAL_EXECUTION_TIME,
    STATS_FOOTER
)

class StatisticsTracker:
    """Tracks statistics about generated content"""
    
    def __init__(self):
        """Initialize the statistics tracker"""
        self.start_time = time.time()
        self.folder_count = 0
        self.file_count = 0
        self.file_types = Counter()
        self.item_processing_times = {}
        self.current_item_start = None
        self.current_item = None
    
    def start_tracking_item(self, item_name: str) -> None:
        """
        Start tracking processing time for an item
        
        Args:
            item_name: Name of the item being processed
        """
        self.current_item = item_name
        self.current_item_start = time.time()
    
    def end_tracking_item(self) -> None:
        """End tracking processing time for the current item"""
        if self.current_item and self.current_item_start:
            processing_time = time.time() - self.current_item_start
            self.item_processing_times[self.current_item] = processing_time
            self.current_item = None
            self.current_item_start = None
    
    def add_folder(self, folder_path: str) -> None:
        """
        Add a folder to statistics
        
        Args:
            folder_path: Path of the folder
        """
        self.folder_count += 1
    
    def add_file(self, file_path: str) -> None:
        """
        Add a file to statistics
        
        Args:
            file_path: Path of the file
        """
        self.file_count += 1
        
        # Track file type
        _, ext = os.path.splitext(file_path)
        if ext:
            # Remove dot from extension
            self.file_types[ext[1:]] += 1
        else:
            self.file_types["no_extension"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get the collected statistics
        
        Returns:
            Dictionary containing statistics
        """
        total_time = time.time() - self.start_time
        
        return {
            "total_execution_time": total_time,
            "folder_count": self.folder_count,
            "file_count": self.file_count,
            "file_types": dict(self.file_types),
            "item_processing_times": self.item_processing_times
        }
    
    def print_statistics(self, language: str = "en") -> None:
        """
        Print collected statistics to console
        
        Args:
            language: Language code (not used with hardcoded strings)
        """
        stats = self.get_statistics()
        
        print(f"\n{STATS_HEADER}")
        print(STATS_FOLDER_COUNT.format(count=stats['folder_count']))
        print(STATS_FILE_COUNT.format(count=stats['file_count']))
        
        print(f"\n{STATS_FILE_TYPES_HEADER}")
        for file_type, count in sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True):
            file_type_item = STATS_FILE_TYPE_ITEM.format(type=file_type, count=count)
            print(f"  - {file_type_item}")
        
        print(f"\n{STATS_PROCESSING_TIMES_HEADER}")
        for item, processing_time in sorted(stats['item_processing_times'].items(), 
                                           key=lambda x: x[1], reverse=True):
            time_item = STATS_PROCESSING_TIME_ITEM.format(item=item, time=f"{processing_time:.2f}")
            print(f"  - {time_item}")
        
        print(f"\n{STATS_TOTAL_EXECUTION_TIME.format(time=f'{stats["total_execution_time"]:.2f}')}")
        print(STATS_FOOTER) 