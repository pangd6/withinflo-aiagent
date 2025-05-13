"""
Configuration module for the QA Documentation Generator
"""

import os
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "qa_doc_generator")

# Redis Configuration
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URI)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URI)

# LLM API Configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")

# Crawler Configuration
DEFAULT_CRAWL_TIMEOUT = int(os.getenv("DEFAULT_CRAWL_TIMEOUT", "30"))
DEFAULT_WAIT_FOR_LOAD = int(os.getenv("DEFAULT_WAIT_FOR_LOAD", "5"))
DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE", "10"))

# Configure Loguru
logger.add(
    "logs/qa_doc_generator.log", 
    rotation="10 MB", 
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

def validate_config() -> tuple[bool, Optional[str]]:
    """
    Validate required configuration settings.
    Returns a tuple with (is_valid, error_message)
    """
    if not LLM_API_KEY:
        return False, "LLM_API_KEY environment variable is required"
    
    return True, None 