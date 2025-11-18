"""
In-memory A2A message adapter.

Provides an in-memory implementation of the A2A protocol adapter for
local development and testing. Messages are stored in memory queues
and support correlation ID propagation and basic tracing.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from src.a2a.protocol import A2AMessage
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class InMemoryA2AAdapter:
    """
    In-memory adapter for A2A message passing.
    
    This adapter maintains message queues in memory for each agent and
    supports subscription-based message delivery with correlation tracking.
    """
    
    def __init__(self) -> None:
        """Initialize the in-memory adapter."""
        self._queues: Dict[str, List[A2AMessage]] = defaultdict(list)
        self._subscribers: Dict[str, List[Callable[[A2AMessage], None]]] = defaultdict(list)
        self._message_history: List[A2AMessage] = []
        self._max_history: int = 1000
        self._lock = asyncio.Lock()
    
    async def send_message(
        self,
        message: A2AMessage,
        receiver: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a receiver or broadcast.
        
        Args:
            message: A2A message to send
            receiver: Receiver agent ID (uses message.meta.receiver if not provided)
            
        Returns:
            True if message was queued successfully
        """
        async with self._lock:
            target = receiver or message.meta.receiver
            
            if target is None:
                logger.warning(
                    "No receiver specified for message",
                    extra={
                        "message_id": message.message_id,
                        "trace_id": message.trace_id,
                    }
                )
                return False
            
            # Add to queue
            self._queues[target].append(message)
            
            # Add to history (limited)
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history.pop(0)
            
            logger.info(
                f"Message sent to {target}",
                extra={
                    "message_id": message.message_id,
                    "message_type": message.message_type,
                    "trace_id": message.trace_id,
                    "correlation_id": message.correlation_id,
                    "sender": message.meta.sender,
                    "receiver": target,
                }
            )
            
            # Notify subscribers
            if target in self._subscribers:
                for callback in self._subscribers[target]:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(
                            f"Error in subscriber callback: {e}",
                            extra={
                                "message_id": message.message_id,
                                "trace_id": message.trace_id,
                                "error": str(e),
                            }
                        )
            
            return True
    
    async def receive_message(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
        message_type: Optional[str] = None,
    ) -> Optional[A2AMessage]:
        """
        Receive the next message from an agent's queue.
        
        Args:
            agent_id: Agent identifier
            timeout: Optional timeout in seconds
            message_type: Optional filter by message type
            
        Returns:
            Next message or None if timeout/queue empty
        """
        start_time = datetime.utcnow()
        
        while True:
            async with self._lock:
                queue = self._queues.get(agent_id, [])
                
                # Filter by message type if specified
                if message_type:
                    for i, msg in enumerate(queue):
                        if msg.message_type == message_type:
                            return queue.pop(i)
                elif queue:
                    return queue.pop(0)
            
            # Check timeout
            if timeout is not None:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    return None
            else:
                return None
            
            # Brief sleep before retry
            await asyncio.sleep(0.1)
    
    async def subscribe(
        self,
        agent_id: str,
        callback: Callable[[A2AMessage], None],
    ) -> None:
        """
        Subscribe to messages for an agent.
        
        Args:
            agent_id: Agent identifier
            callback: Callback function to invoke on message receipt
        """
        async with self._lock:
            self._subscribers[agent_id].append(callback)
            logger.info(f"Subscribed callback for agent {agent_id}")
    
    async def unsubscribe(
        self,
        agent_id: str,
        callback: Callable[[A2AMessage], None],
    ) -> None:
        """
        Unsubscribe from messages for an agent.
        
        Args:
            agent_id: Agent identifier
            callback: Callback function to remove
        """
        async with self._lock:
            if agent_id in self._subscribers and callback in self._subscribers[agent_id]:
                self._subscribers[agent_id].remove(callback)
                logger.info(f"Unsubscribed callback for agent {agent_id}")
    
    async def get_message_history(
        self,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[A2AMessage]:
        """
        Get message history with optional filtering.
        
        Args:
            trace_id: Filter by trace ID
            correlation_id: Filter by correlation ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages matching criteria
        """
        async with self._lock:
            messages = self._message_history.copy()
            
            if trace_id:
                messages = [m for m in messages if m.trace_id == trace_id]
            
            if correlation_id:
                messages = [m for m in messages if m.correlation_id == correlation_id]
            
            return messages[-limit:]
    
    async def clear_queue(self, agent_id: str) -> int:
        """
        Clear all messages from an agent's queue.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Number of messages cleared
        """
        async with self._lock:
            count = len(self._queues.get(agent_id, []))
            self._queues[agent_id] = []
            logger.info(f"Cleared {count} messages from {agent_id} queue")
            return count
    
    def get_queue_size(self, agent_id: str) -> int:
        """
        Get the current size of an agent's message queue.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Number of messages in queue
        """
        return len(self._queues.get(agent_id, []))


# Global singleton instance
_adapter: Optional[InMemoryA2AAdapter] = None


def get_a2a_adapter() -> InMemoryA2AAdapter:
    """Get the global A2A adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = InMemoryA2AAdapter()
    return _adapter
