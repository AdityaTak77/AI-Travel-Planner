"""
Agent-to-Agent (A2A) Protocol Implementation.

This module implements the A2A message protocol for inter-agent communication
including JSON message schema, versioning, and HMAC-based message signing/verification.

MCP (Model Context Protocol) Compatibility:
- A2A messages follow MCP standard envelope structure
- Supports tool invocation via MCP tooling framework
- Integrates with src/integrations/mcp_client.py for tool discovery/invocation
- Trace ID and correlation ID enable MCP distributed tracing

Tools Integrated via MCP:
1. Gemini 2.0 Flash (research)
2. Groq LLM (generation)
3. DuckDuckGo Search (search)
4. Calculator (calculations)
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.config.settings import get_settings


class A2AMessageType(str):
    """A2A message types."""
    
    # Lifecycle
    HANDSHAKE = "handshake"
    ACK = "ack"
    
    # Planning
    PROPOSAL = "proposal"
    OPTIMIZED_PLAN = "optimized_plan"
    
    # Data sharing
    STATE_UPDATE = "state_update"
    QUERY = "query"
    RESPONSE = "response"
    
    # Control
    ERROR = "error"
    CANCEL = "cancel"


class A2AMetadata(BaseModel):
    """Metadata for A2A messages."""
    
    sender: str = Field(description="Sender agent identifier")
    receiver: Optional[str] = Field(default=None, description="Receiver agent identifier")
    priority: int = Field(default=5, description="Message priority (1-10, higher=more urgent)")
    ttl: int = Field(default=300, description="Time-to-live in seconds")


class A2AMessage(BaseModel):
    """
    Agent-to-Agent message envelope.
    
    This is the standard message format for all inter-agent communication.
    Messages are HMAC-signed for integrity and authenticity.
    """
    
    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message identifier"
    )
    trace_id: str = Field(description="Distributed trace ID")
    correlation_id: str = Field(description="Request correlation ID")
    message_type: str = Field(description="Message type identifier")
    version: str = Field(default="1.0", description="Protocol version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message creation timestamp"
    )
    payload: Dict[str, Any] = Field(description="Message payload")
    meta: A2AMetadata = Field(description="Message metadata")
    signature: Optional[str] = Field(default=None, description="HMAC signature")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = self.model_dump()
        # Convert datetime to ISO format string
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)


def compute_hmac_signature(message: A2AMessage, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for a message.
    
    Args:
        message: A2A message to sign
        secret: Shared secret key
        
    Returns:
        Hexadecimal HMAC signature
    """
    # Create canonical representation (excluding signature field)
    message_dict = message.to_dict()
    message_dict.pop("signature", None)
    
    # Custom JSON encoder to handle Decimal and datetime types
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            from decimal import Decimal
            from datetime import datetime, date
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)
    
    # Sort keys for deterministic signing
    canonical = json.dumps(message_dict, sort_keys=True, cls=CustomEncoder)
    
    # Compute HMAC
    signature = hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def sign_message(message: A2AMessage, secret: Optional[str] = None) -> A2AMessage:
    """
    Sign an A2A message with HMAC signature.
    
    Args:
        message: Message to sign
        secret: Shared secret (uses settings if not provided)
        
    Returns:
        Signed message
    """
    if secret is None:
        settings = get_settings()
        secret = settings.a2a_shared_secret
    
    signature = compute_hmac_signature(message, secret)
    message.signature = signature
    return message


def verify_message(message: A2AMessage, secret: Optional[str] = None) -> bool:
    """
    Verify HMAC signature of an A2A message.
    
    Args:
        message: Message to verify
        secret: Shared secret (uses settings if not provided)
        
    Returns:
        True if signature is valid, False otherwise
    """
    if message.signature is None:
        return False
    
    if secret is None:
        settings = get_settings()
        secret = settings.a2a_shared_secret
    
    expected_signature = compute_hmac_signature(message, secret)
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(message.signature, expected_signature)


def create_message(
    message_type: str,
    payload: Dict[str, Any],
    trace_id: str,
    correlation_id: str,
    sender: str,
    receiver: Optional[str] = None,
    sign: bool = True,
) -> A2AMessage:
    """
    Create and optionally sign an A2A message.
    
    Args:
        message_type: Type of message
        payload: Message payload
        trace_id: Distributed trace ID
        correlation_id: Request correlation ID
        sender: Sender agent identifier
        receiver: Receiver agent identifier (optional for broadcast)
        sign: Whether to sign the message (default True)
        
    Returns:
        Created (and optionally signed) A2A message
    """
    message = A2AMessage(
        message_type=message_type,
        payload=payload,
        trace_id=trace_id,
        correlation_id=correlation_id,
        meta=A2AMetadata(sender=sender, receiver=receiver),
    )
    
    if sign:
        message = sign_message(message)
    
    return message


def create_proposal_message(
    proposal_data: Dict[str, Any],
    trace_id: str,
    correlation_id: str,
    sender: str,
    receiver: Optional[str] = None,
) -> A2AMessage:
    """
    Create a proposal message (used by CrewAI agent).
    
    Args:
        proposal_data: Proposal payload data
        trace_id: Trace ID
        correlation_id: Correlation ID
        sender: Sender agent ID
        receiver: Receiver agent ID
        
    Returns:
        Signed proposal message
    """
    return create_message(
        message_type=A2AMessageType.PROPOSAL,
        payload=proposal_data,
        trace_id=trace_id,
        correlation_id=correlation_id,
        sender=sender,
        receiver=receiver,
    )


def create_optimized_plan_message(
    plan_data: Dict[str, Any],
    trace_id: str,
    correlation_id: str,
    sender: str,
    receiver: Optional[str] = None,
) -> A2AMessage:
    """
    Create an optimized plan message (used by ADK agent).
    
    Args:
        plan_data: Optimized plan payload
        trace_id: Trace ID
        correlation_id: Correlation ID
        sender: Sender agent ID
        receiver: Receiver agent ID
        
    Returns:
        Signed optimized plan message
    """
    return create_message(
        message_type=A2AMessageType.OPTIMIZED_PLAN,
        payload=plan_data,
        trace_id=trace_id,
        correlation_id=correlation_id,
        sender=sender,
        receiver=receiver,
    )


def create_error_message(
    error_data: Dict[str, Any],
    trace_id: str,
    correlation_id: str,
    sender: str,
    receiver: Optional[str] = None,
) -> A2AMessage:
    """
    Create an error message.
    
    Args:
        error_data: Error details
        trace_id: Trace ID
        correlation_id: Correlation ID
        sender: Sender agent ID
        receiver: Receiver agent ID
        
    Returns:
        Signed error message
    """
    return create_message(
        message_type=A2AMessageType.ERROR,
        payload=error_data,
        trace_id=trace_id,
        correlation_id=correlation_id,
        sender=sender,
        receiver=receiver,
    )
