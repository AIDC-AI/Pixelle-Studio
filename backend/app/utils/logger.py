"""
Centralized logging configuration for the application.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Get the backend directory (parent of app)
BACKEND_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BACKEND_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create logger
logger = logging.getLogger("mcp_workflow")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers if this module is imported multiple times
if not logger.handlers:
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler for all logs (with rotation)
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # File handler for errors only
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)


# Convenience functions
def get_logger(name: str = None):
    """
    Get a logger instance.
    
    Args:
        name: Optional name for the logger. If provided, returns a child logger.
    
    Returns:
        Logger instance
    """
    if name:
        return logger.getChild(name)
    return logger


# Export the main logger instance
log = logger

