"""
Main application entry point for the QA Documentation Generator.
"""

import uvicorn
from loguru import logger

from src.api.app import app
from src.config import API_HOST, API_PORT, validate_config


def main():
    """Run the FastAPI application."""
    logger.info("Starting QA Documentation Generator")
    
    # Validate configuration
    valid, error_message = validate_config()
    if not valid:
        logger.error(f"Invalid configuration: {error_message}")
        return
    
    # Run the server
    uvicorn.run(
        "src.api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main() 