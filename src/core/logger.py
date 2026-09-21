"""Logging configuration for the MCP server."""
import logging
import sys
import os


def setup_logging():
    """Configure logging for the application."""
    # AC_LOG_MIN_LEVEL is the new name (BE-8827, matches every onboarded .NET service's own
    # ASPNETCORE_LOG_MIN_LEVEL -> AC_LOG_MIN_LEVEL rename); LOG_LEVEL is kept as a fallback.
    # Read at import time (this module-level call runs before main()/_bootstrap_hosted_config()
    # ever executes), so a hosted deployment's Config-Service-resolved value can't reach this -
    # accepted, documented limitation, see _bootstrap_hosted_config()'s own docstring in server.py.
    log_level = (os.getenv("AC_LOG_MIN_LEVEL") or os.getenv("LOG_LEVEL") or "INFO").upper()
    
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