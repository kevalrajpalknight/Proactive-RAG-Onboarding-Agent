"""Logging configuration for the agent."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> None:
    """
    Set up logging configuration for the agent.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
        format_string: Custom log format string
    """
    
    # Default format
    if not format_string:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(file_handler)
    
    # Set specific loggers to appropriate levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.INFO)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("faiss").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured at {level} level")
    if log_file:
        logging.info(f"Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)