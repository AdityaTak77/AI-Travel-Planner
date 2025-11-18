"""
Application settings loaded from environment variables.

Uses Pydantic BaseSettings to automatically load and validate configuration
from environment variables and .env files.
"""

from typing import Optional

from pydantic import Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Application
    app_env: str = Field(default="development", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Security
    a2a_shared_secret: str = Field(description="Shared secret for A2A HMAC signing")
    
    # External API Keys
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq model to use")
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model to use"
    )
    
    # State Management
    state_backend: str = Field(
        default="inmemory",
        description="State backend type: inmemory or redis"
    )
    
    # Monitoring
    enable_monitoring: bool = Field(default=True, description="Enable monitoring callbacks")
    
    # Feature Flags
    allow_booking_operations: bool = Field(
        default=False,
        description="Allow actual booking operations (vs demo mode)"
    )
    
    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "ignore"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == "development"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings
