"""Logging configuration for the MCP server."""
import logging
import sys
import os


def setup_logging():
    """Configure logging for the application."""
    # Get log level from environment (default to INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    return logging.getLogger("Appcircle MCP")


# Create logger instance
logger = setup_logging()