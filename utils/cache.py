import time
from typing import Dict, Any, Optional, Tuple

class SimpleCache:
    """
    A simple in-memory cache for API responses
    
    This reduces redundant API calls by storing results with an expiration time
    """
    
    def __init__(self, default_expiry: int = 3600):
        """
        Initialize the cache
        
        Args:
            default_expiry: Default expiration time in seconds (1 hour default)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_expiry = default_expiry
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and is not expired
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if entry["expires_at"] < time.time():
            # Entry has expired, remove it
            del self.cache[key]
            return None
            
        return entry["value"]
        
    def set(self, key: str, value: Any, expiry: Optional[int] = None) -> None:
        """
        Set a value in the cache with expiration
        
        Args:
            key: The cache key
            value: The value to cache
            expiry: Expiration time in seconds (uses default if None)
        """
        expires_at = time.time() + (expiry if expiry is not None else self.default_expiry)
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        
    def delete(self, key: str) -> None:
        """Delete a key from the cache if it exists"""
        if key in self.cache:
            del self.cache[key]
            
    def clear(self) -> None:
        """Clear the entire cache"""
        self.cache.clear()
        
    def clean_expired(self) -> int:
        """
        Remove all expired entries from the cache
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry["expires_at"] < now
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        return len(expired_keys)
        
    def create_key(self, *args, **kwargs) -> str:
        """
        Create a cache key from arguments
        
        This helps create consistent keys for the same inputs
        """
        # Simple key creation by concatenating string values
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)
        
# Global cache instance
cache = SimpleCache() 