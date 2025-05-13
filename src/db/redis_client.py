"""
Redis client for job queuing and rate limiting.
"""

import time
from typing import List, Optional, Dict, Any

import redis
from loguru import logger

from src.config import REDIS_URI


class RedisClient:
    """Redis client for job queuing and rate limiting."""
    
    def __init__(self):
        self.client = None
    
    def connect(self) -> None:
        """Connect to Redis."""
        try:
            logger.info(f"Connecting to Redis at {REDIS_URI}")
            self.client = redis.from_url(REDIS_URI)
            self.client.ping()  # Test the connection
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def close(self) -> None:
        """Close the Redis connection."""
        if self.client:
            self.client.close()
            logger.info("Closed Redis connection")
    
    def check_rate_limit(self, domain: str, requests_per_minute: int) -> bool:
        """
        Check if a domain has reached its rate limit.
        
        Args:
            domain: The domain to check
            requests_per_minute: Maximum requests per minute
            
        Returns:
            True if the request can proceed, False if rate limited
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return True
        
        now = int(time.time())
        key = f"rate_limit:{domain}"
        
        # Get the current count and timestamps
        self.client.zremrangebyscore(key, 0, now - 60)  # Remove entries older than 1 minute
        count = self.client.zcard(key)
        
        if count >= requests_per_minute:
            logger.warning(f"Rate limit reached for domain {domain}: {count} requests in the last minute")
            return False
        
        # Add the current timestamp
        self.client.zadd(key, {str(now): now})
        self.client.expire(key, 120)  # Set a 2-minute expiry as a safety margin
        
        return True
    
    def cache_dom_snapshot(self, url: str, dom_content: str, ttl_seconds: int = 300) -> None:
        """
        Cache DOM content for a URL.
        
        Args:
            url: The URL
            dom_content: The DOM content to cache
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return
        
        key = f"dom_snapshot:{url}"
        self.client.setex(key, ttl_seconds, dom_content)
        logger.info(f"Cached DOM snapshot for URL: {url} (TTL: {ttl_seconds}s)")
    
    def get_dom_snapshot(self, url: str) -> Optional[str]:
        """
        Get cached DOM content for a URL.
        
        Args:
            url: The URL
            
        Returns:
            The cached DOM content, or None if not found
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return None
        
        key = f"dom_snapshot:{url}"
        dom_content = self.client.get(key)
        
        if dom_content:
            logger.info(f"Retrieved cached DOM snapshot for URL: {url}")
            return dom_content.decode('utf-8')
        
        return None


# Singleton instance
redis_client = RedisClient() 