"""
State store for sharing intermediate results between agents.

Provides an interface for state management and implementations for
in-memory and Redis backends.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class StateStore(ABC):
    """Abstract interface for state storage."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the store.
        
        Args:
            key: State key
            
        Returns:
            Value or None if not found
        """
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the store.
        
        Args:
            key: State key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the store.
        
        Args:
            key: State key
            
        Returns:
            True if key existed and was deleted
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the store.
        
        Args:
            key: State key
            
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all keys in the store.
        
        Args:
            pattern: Optional pattern to filter keys (e.g., "flight:*")
            
        Returns:
            List of matching keys
        """
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """
        Clear all data from the store.
        
        Returns:
            Number of keys deleted
        """
        pass


class InMemoryStateStore(StateStore):
    """
    In-memory implementation of state store.
    
    Suitable for development and testing. Data is lost when process terminates.
    """
    
    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
    
    def _cleanup_expired(self) -> None:
        """Remove expired keys."""
        now = datetime.utcnow()
        expired = [key for key, expiry in self._expiry.items() if expiry <= now]
        for key in expired:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the store."""
        self._cleanup_expired()
        value = self._store.get(key)
        
        if value is not None:
            logger.debug(f"State retrieved: {key}")
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the store."""
        self._cleanup_expired()
        self._store[key] = value
        
        if ttl is not None:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        else:
            self._expiry.pop(key, None)
        
        logger.debug(f"State stored: {key} (ttl={ttl})")
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a value from the store."""
        self._cleanup_expired()
        
        if key in self._store:
            del self._store[key]
            self._expiry.pop(key, None)
            logger.debug(f"State deleted: {key}")
            return True
        
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        self._cleanup_expired()
        return key in self._store
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys in the store."""
        self._cleanup_expired()
        keys = list(self._store.keys())
        
        if pattern:
            # Simple wildcard matching (* at start/end)
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                keys = [k for k in keys if k.startswith(prefix)]
            elif pattern.startswith("*"):
                suffix = pattern[1:]
                keys = [k for k in keys if k.endswith(suffix)]
            else:
                keys = [k for k in keys if pattern in k]
        
        return keys
    
    async def clear(self) -> int:
        """Clear all data from the store."""
        count = len(self._store)
        self._store.clear()
        self._expiry.clear()
        logger.info(f"State store cleared: {count} keys removed")
        return count


class RedisStateStore(StateStore):
    """
    Redis-based state store implementation.
    
    NOTE: This is a stub implementation. In production, you would:
    1. Install redis-py: pip install redis
    2. Initialize Redis client with connection URL
    3. Implement async operations using aioredis or redis-py async support
    """
    
    def __init__(self, redis_url: str) -> None:
        """
        Initialize Redis store.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        # TODO: Initialize Redis client
        # self._redis = redis.from_url(redis_url)
        logger.warning("RedisStateStore is a stub implementation")
        raise NotImplementedError(
            "Redis support requires redis-py package. "
            "Install with: pip install redis"
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        # TODO: Implement Redis get
        raise NotImplementedError()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis."""
        # TODO: Implement Redis set with optional TTL
        raise NotImplementedError()
    
    async def delete(self, key: str) -> bool:
        """Delete a value from Redis."""
        # TODO: Implement Redis delete
        raise NotImplementedError()
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        # TODO: Implement Redis exists
        raise NotImplementedError()
    
    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List keys in Redis."""
        # TODO: Implement Redis keys/scan
        raise NotImplementedError()
    
    async def clear(self) -> int:
        """Clear all data from Redis."""
        # TODO: Implement Redis flushdb
        raise NotImplementedError()


def create_state_store(backend: str = "inmemory", redis_url: Optional[str] = None) -> StateStore:
    """
    Factory function to create a state store.
    
    Args:
        backend: Backend type ("inmemory" or "redis")
        redis_url: Redis connection URL (required for redis backend)
        
    Returns:
        StateStore instance
        
    Raises:
        ValueError: If backend is invalid or required parameters missing
    """
    if backend == "inmemory":
        logger.info("Creating in-memory state store")
        return InMemoryStateStore()
    elif backend == "redis":
        if not redis_url:
            raise ValueError("redis_url is required for redis backend")
        logger.info(f"Creating Redis state store: {redis_url}")
        return RedisStateStore(redis_url)
    else:
        raise ValueError(f"Unknown state backend: {backend}")


# Global singleton instance
_state_store: Optional[StateStore] = None


async def get_state_store() -> StateStore:
    """Get the global state store instance."""
    global _state_store
    if _state_store is None:
        from src.config.settings import get_settings
        settings = get_settings()
        _state_store = create_state_store(
            backend=settings.state_backend,
            redis_url=settings.redis_url if settings.state_backend == "redis" else None,
        )
    return _state_store
