import logging
import os
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from ydrpolicy.data_collection.config import config

class DataCollectionLogger:
    """Custom logger class using Rich for formatting and file output"""
    
    def __init__(self, name: str = "DataCollectionLogger", level: int = logging.INFO, path: Optional[str] = None):
        """Initialize the logger with Rich formatting and file output

        Args:
            name: The name of the logger
            level: The logging level (default: logging.INFO)
            path: Optional file path to save logs. If None, logs will only be displayed in the console
        """
        # Create a Rich console
        self.console = Console()
        
        # Create the logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove any existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        # Add Rich handler for terminal output with nice formatting
        rich_handler = RichHandler(
            rich_tracebacks=True,
            console=self.console,
            show_time=True,
            show_path=False
        )
        rich_handler.setLevel(level)
        self.logger.addHandler(rich_handler)
        
        # Add file handler if a log file is specified
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Standard formatter for file logs
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Create and configure file handler
            file_handler = logging.FileHandler(
                path, 
                mode='a' if os.path.exists(path) else 'w', 
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level)
            
            # Add file handler to the logger
            self.logger.addHandler(file_handler)
            
            # Log that we initialized with a file
            self.logger.info(f"Logging initialized. Log file: {path}")
        else:
            self.logger.info("Logging initialized (console only)")

    def info(self, message: str) -> None:
        """Log info level message"""
        self.logger.info(message)
        
    def error(self, message: str) -> None:
        """Log error level message"""
        self.logger.error(message)
        
    def debug(self, message: str) -> None:
        """Log debug level message"""
        self.logger.debug(message)
        
    def warning(self, message: str) -> None:
        """Log warning level message"""
        self.logger.warning(message)
    
    def success(self, message: str) -> None:
        """Log success as an info message with success prefix"""
        self.logger.info(f"[green]SUCCESS:[/green] {message}")
        
    def failure(self, message: str) -> None:
        """Log failure as an error message with failure prefix"""
        self.logger.error(f"[red]FAILURE:[/red] {message}")
        
    def progress(self, message: str) -> None:
        """Log progress as an info message with progress prefix"""
        self.logger.info(f"[blue]PROGRESS:[/blue] {message}")