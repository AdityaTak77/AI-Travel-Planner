"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def mock_settings() -> dict:
    """Provide mock settings for tests."""
    return {
        "app_env": "test",
        "log_level": "DEBUG",
        "state_backend": "inmemory",
        "enable_monitoring": True,
        "allow_booking_operations": False,
    }
