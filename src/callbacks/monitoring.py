"""
Monitoring callbacks for task execution tracking.

Provides callback functions that emit MonitoringEvent instances
for observability and debugging.
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.models.itinerary import EventSeverity, EventType, MonitoringEvent
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class MonitoringCallbacks:
    """
    Collection of monitoring callbacks.
    
    These callbacks track task lifecycle, state changes, and errors,
    emitting structured MonitoringEvent instances.
    """
    
    def __init__(self, trace_id: str, correlation_id: str) -> None:
        """
        Initialize monitoring callbacks.
        
        Args:
            trace_id: Distributed trace ID
            correlation_id: Request correlation ID
        """
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self._listeners: List[Callable[[MonitoringEvent], None]] = []
    
    def register_listener(self, listener: Callable[[MonitoringEvent], None]) -> None:
        """
        Register a listener for monitoring events.
        
        Args:
            listener: Callback function that receives MonitoringEvent
        """
        self._listeners.append(listener)
    
    def _emit_event(self, event: MonitoringEvent) -> None:
        """
        Emit a monitoring event to all listeners.
        
        Args:
            event: Event to emit
        """
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in monitoring listener: {e}")
    
    def on_task_start(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
        message: str = "Task started",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when a task starts.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            message: Event message
            data: Additional event data
        """
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_START,
            severity=EventSeverity.INFO,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=message,
            data=data or {},
        )
        
        self._emit_event(event)
        
        logger.info(
            message,
            extra={
                "event_type": "task_start",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
            }
        )
    
    def on_task_progress(
        self,
        task_id: str,
        progress: float,
        agent_id: Optional[str] = None,
        message: str = "Task in progress",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called to report task progress.
        
        Args:
            task_id: Task identifier
            progress: Progress value (0.0-1.0)
            agent_id: Agent identifier
            message: Event message
            data: Additional event data
        """
        event_data = data or {}
        event_data["progress"] = progress
        
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_PROGRESS,
            severity=EventSeverity.INFO,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=message,
            data=event_data,
        )
        
        self._emit_event(event)
        
        logger.info(
            f"{message} ({progress:.1%})",
            extra={
                "event_type": "task_progress",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "progress": progress,
            }
        )
    
    def on_task_end(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
        message: str = "Task completed",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when a task completes successfully.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            message: Event message
            data: Additional event data
        """
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_END,
            severity=EventSeverity.INFO,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=message,
            data=data or {},
        )
        
        self._emit_event(event)
        
        logger.info(
            message,
            extra={
                "event_type": "task_end",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
            }
        )
    
    def on_task_error(
        self,
        task_id: str,
        error: Exception,
        agent_id: Optional[str] = None,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when a task encounters an error.
        
        Args:
            task_id: Task identifier
            error: Exception that occurred
            agent_id: Agent identifier
            message: Event message
            data: Additional event data
        """
        error_message = message or f"Task error: {str(error)}"
        
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_ERROR,
            severity=EventSeverity.ERROR,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=error_message,
            data=data or {},
            error={
                "type": type(error).__name__,
                "message": str(error),
            },
        )
        
        self._emit_event(event)
        
        logger.error(
            error_message,
            extra={
                "event_type": "task_error",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "error_type": type(error).__name__,
            }
        )
    
    def on_state_change(
        self,
        task_id: str,
        key: str,
        old_value: Any,
        new_value: Any,
        agent_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Called when state changes.
        
        Args:
            task_id: Task identifier
            key: State key that changed
            old_value: Previous value
            new_value: New value
            agent_id: Agent identifier
            message: Event message
        """
        event_message = message or f"State changed: {key}"
        
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.STATE_CHANGE,
            severity=EventSeverity.DEBUG,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=event_message,
            data={
                "key": key,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
            },
        )
        
        self._emit_event(event)
        
        logger.debug(
            event_message,
            extra={
                "event_type": "state_change",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "key": key,
            }
        )
    
    def on_agent_message(
        self,
        task_id: str,
        agent_id: str,
        message_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when an agent sends a message.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            message_type: Type of agent message
            message: Event message
            data: Additional event data
        """
        event_data = data or {}
        event_data["message_type"] = message_type
        
        event = MonitoringEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.AGENT_MESSAGE,
            severity=EventSeverity.INFO,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            task_id=task_id,
            agent_id=agent_id,
            message=message,
            data=event_data,
        )
        
        self._emit_event(event)
        
        logger.info(
            message,
            extra={
                "event_type": "agent_message",
                "trace_id": self.trace_id,
                "correlation_id": self.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "message_type": message_type,
            }
        )
