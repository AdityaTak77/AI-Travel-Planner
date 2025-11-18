"""
Unit tests for state store.

Tests state storage and retrieval operations.
"""

import pytest

from src.state.store import InMemoryStateStore, create_state_store


@pytest.mark.asyncio
async def test_inmemory_store_set_get() -> None:
    """Test basic set and get operations."""
    store = InMemoryStateStore()
    
    # Set value
    success = await store.set("test-key", {"data": "value"})
    assert success
    
    # Get value
    value = await store.get("test-key")
    assert value == {"data": "value"}


@pytest.mark.asyncio
async def test_inmemory_store_delete() -> None:
    """Test delete operation."""
    store = InMemoryStateStore()
    
    await store.set("key1", "value1")
    
    # Delete existing key
    deleted = await store.delete("key1")
    assert deleted
    
    # Try to get deleted key
    value = await store.get("key1")
    assert value is None
    
    # Delete non-existent key
    deleted = await store.delete("non-existent")
    assert not deleted


@pytest.mark.asyncio
async def test_inmemory_store_exists() -> None:
    """Test exists operation."""
    store = InMemoryStateStore()
    
    await store.set("existing", "value")
    
    assert await store.exists("existing")
    assert not await store.exists("non-existent")


@pytest.mark.asyncio
async def test_inmemory_store_list_keys() -> None:
    """Test list keys operation."""
    store = InMemoryStateStore()
    
    await store.set("flight:123", {"type": "flight"})
    await store.set("flight:456", {"type": "flight"})
    await store.set("hotel:789", {"type": "hotel"})
    
    # List all keys
    all_keys = await store.list_keys()
    assert len(all_keys) == 3
    
    # List with pattern
    flight_keys = await store.list_keys("flight:*")
    assert len(flight_keys) == 2
    assert all(k.startswith("flight:") for k in flight_keys)


@pytest.mark.asyncio
async def test_inmemory_store_ttl() -> None:
    """Test TTL (time-to-live) expiration."""
    store = InMemoryStateStore()
    
    # Set with very short TTL
    await store.set("expires-soon", "value", ttl=1)
    
    # Should exist immediately
    assert await store.exists("expires-soon")
    
    # Wait for expiration
    import asyncio
    await asyncio.sleep(1.1)
    
    # Should be expired
    value = await store.get("expires-soon")
    assert value is None


@pytest.mark.asyncio
async def test_inmemory_store_clear() -> None:
    """Test clear operation."""
    store = InMemoryStateStore()
    
    await store.set("key1", "value1")
    await store.set("key2", "value2")
    await store.set("key3", "value3")
    
    # Clear all
    count = await store.clear()
    assert count == 3
    
    # Verify empty
    keys = await store.list_keys()
    assert len(keys) == 0


@pytest.mark.asyncio
async def test_create_state_store_factory() -> None:
    """Test state store factory function."""
    # Create in-memory store
    store = create_state_store("inmemory")
    assert isinstance(store, InMemoryStateStore)
    
    # Invalid backend should raise error
    with pytest.raises(ValueError):
        create_state_store("invalid-backend")


@pytest.mark.asyncio
async def test_state_store_complex_values() -> None:
    """Test storing complex Python objects."""
    store = InMemoryStateStore()
    
    complex_value = {
        "flights": [
            {"id": "f1", "price": 450.00},
            {"id": "f2", "price": 520.00},
        ],
        "metadata": {
            "timestamp": "2025-11-18T00:00:00Z",
            "count": 2,
        },
    }
    
    await store.set("complex", complex_value)
    
    retrieved = await store.get("complex")
    assert retrieved == complex_value
    assert len(retrieved["flights"]) == 2
