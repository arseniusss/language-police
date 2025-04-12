import logging
import sys
import io
from pathlib import Path

def setup_logger():
    """
    Configure and return a logger that can be shared across modules
    with proper Unicode handling
    """
    # Create logger
    logger = logging.getLogger('backend')
    logger.setLevel(logging.INFO)

    # Check if handlers already exist to avoid duplicates
    if not logger.handlers:
        # Create console handler with proper encoding
        if sys.platform == 'win32':
            # On Windows, use utf-8 encoding for console output
            console_handler = logging.StreamHandler(
                stream=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            )
        else:
            # On other platforms, regular stdout should work fine
            console_handler = logging.StreamHandler(sys.stdout)
            
        console_handler.setLevel(logging.INFO)

        # Create file handler with utf-8 encoding
        logs_dir = Path(__file__).parent.parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            logs_dir / 'backend.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

# Get a configured logger
logger = setup_logger()