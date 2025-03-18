import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration to write logs to both console and daily rotating files.
    
    Args:
        log_level: The logging level (default: logging.INFO)
    
    Returns:
        logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear any existing handlers to avoid duplicate logs
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler - daily rotation at midnight
    log_file = os.path.join(logs_dir, 'bot.log')
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep logs for 30 days
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d.log"  # Append date to the filename
    logger.addHandler(file_handler)
    
    # Disable httpx and telegram.ext polling logs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext.Application').setLevel(logging.WARNING)
    
    return logger

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name: Name for the logger
        
    Returns:
        logger: Logger instance
    """
    return logging.getLogger(name)