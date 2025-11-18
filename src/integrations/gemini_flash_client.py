"""
Gemini 2.0 Flash API client wrapper.

Provides a thin client for Google Gemini API with typed responses.
Used for text generation and natural language processing.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class GeminiMessage(BaseModel):
    """A message in a Gemini conversation."""
    
    role: str = Field(description="Message role (user/assistant)")
    content: str = Field(description="Message content")


class GeminiGenerationConfig(BaseModel):
    """Configuration for text generation."""
    
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=1024, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, description="Nucleus sampling parameter")
    top_k: int = Field(default=40, description="Top-k sampling parameter")


class GeminiResponse(BaseModel):
    """Response from Gemini API."""
    
    text: str = Field(description="Generated text")
    model: str = Field(description="Model used")
    finish_reason: str = Field(default="stop", description="Reason generation stopped")
    usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Token usage statistics"
    )


class GeminiFlashClient:
    """
    Client for Google Gemini 2.0 Flash API.
    
    NOTE: This is a skeleton implementation. In production:
    1. Use google-generativeai package or direct REST API
    2. Implement proper authentication and retry logic
    3. Handle rate limiting and errors
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1",
    ) -> None:
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key (uses settings if not provided)
            model: Model name (uses settings if not provided)
            base_url: Base URL for Gemini API
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=60.0)
    
    async def generate(
        self,
        prompt: str,
        config: Optional[GeminiGenerationConfig] = None,
        system_instruction: Optional[str] = None,
    ) -> GeminiResponse:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            config: Generation configuration
            system_instruction: Optional system instruction
            
        Returns:
            Generated response
        """
        if config is None:
            config = GeminiGenerationConfig()
        
        logger.info(
            f"Gemini generate: {prompt[:100]}...",
            extra={"model": self.model, "temperature": config.temperature}
        )
        
        # TODO: Replace with actual Gemini API call
        if not self.api_key or self.api_key.startswith("placeholder"):
            logger.warning("Using stub Gemini client - returning mock response")
            return GeminiResponse(
                text=f"[MOCK RESPONSE] Generated content for: {prompt[:50]}...",
                model=self.model,
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            )
        
        # Real API call (skeleton)
        try:
            url = f"{self.base_url}/models/{self.model}:generateContent"
            params = {"key": self.api_key}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": config.temperature,
                    "maxOutputTokens": config.max_tokens,
                    "topP": config.top_p,
                    "topK": config.top_k,
                },
            }
            
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
            
            response = await self._client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract generated text
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            return GeminiResponse(
                text=text,
                model=self.model,
                finish_reason=data.get("candidates", [{}])[0].get("finishReason", "stop"),
                usage=data.get("usageMetadata", {}),
            )
        except httpx.HTTPError as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[GeminiMessage],
        config: Optional[GeminiGenerationConfig] = None,
    ) -> GeminiResponse:
        """
        Generate response in a chat conversation.
        
        Args:
            messages: Conversation history
            config: Generation configuration
            
        Returns:
            Generated response
        """
        # Convert messages to prompt format
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        return await self.generate(prompt, config)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self) -> "GeminiFlashClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
