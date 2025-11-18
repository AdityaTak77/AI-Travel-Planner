"""
Unit tests for monitoring callbacks.

Tests callback invocation and event emission.
"""

import pytest

from src.callbacks.monitoring import MonitoringCallbacks
from src.models.itinerary import EventType, EventSeverity, MonitoringEvent


def test_monitoring_callbacks_creation() -> None:
    """Test MonitoringCallbacks initialization."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-123",
        correlation_id="corr-456",
    )
    
    assert callbacks.trace_id == "trace-123"
    assert callbacks.correlation_id == "corr-456"


def test_on_task_start() -> None:
    """Test on_task_start callback."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events_received = []
    
    def listener(event: MonitoringEvent) -> None:
        events_received.append(event)
    
    callbacks.register_listener(listener)
    
    callbacks.on_task_start(
        task_id="task-1",
        agent_id="agent-1",
        message="Task started",
    )
    
    assert len(events_received) == 1
    event = events_received[0]
    assert event.event_type == EventType.TASK_START
    assert event.task_id == "task-1"
    assert event.agent_id == "agent-1"


def test_on_task_progress() -> None:
    """Test on_task_progress callback."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events_received = []
    callbacks.register_listener(lambda e: events_received.append(e))
    
    callbacks.on_task_progress(
        task_id="task-1",
        progress=0.5,
        agent_id="agent-1",
        message="50% complete",
    )
    
    assert len(events_received) == 1
    event = events_received[0]
    assert event.event_type == EventType.TASK_PROGRESS
    assert event.data["progress"] == 0.5


def test_on_task_error() -> None:
    """Test on_task_error callback."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events_received = []
    callbacks.register_listener(lambda e: events_received.append(e))
    
    error = ValueError("Test error")
    
    callbacks.on_task_error(
        task_id="task-1",
        error=error,
        agent_id="agent-1",
    )
    
    assert len(events_received) == 1
    event = events_received[0]
    assert event.event_type == EventType.TASK_ERROR
    assert event.severity == EventSeverity.ERROR
    assert event.error is not None
    assert event.error["type"] == "ValueError"


def test_multiple_listeners() -> None:
    """Test multiple event listeners."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events1 = []
    events2 = []
    
    callbacks.register_listener(lambda e: events1.append(e))
    callbacks.register_listener(lambda e: events2.append(e))
    
    callbacks.on_task_start(
        task_id="task-1",
        message="Test",
    )
    
    # Both listeners should receive the event
    assert len(events1) == 1
    assert len(events2) == 1
    assert events1[0].event_id == events2[0].event_id


def test_on_state_change() -> None:
    """Test on_state_change callback."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events_received = []
    callbacks.register_listener(lambda e: events_received.append(e))
    
    callbacks.on_state_change(
        task_id="task-1",
        key="flight_options",
        old_value=None,
        new_value=["flight1", "flight2"],
        agent_id="agent-1",
    )
    
    assert len(events_received) == 1
    event = events_received[0]
    assert event.event_type == EventType.STATE_CHANGE
    assert event.data["key"] == "flight_options"


def test_on_agent_message() -> None:
    """Test on_agent_message callback."""
    callbacks = MonitoringCallbacks(
        trace_id="trace-1",
        correlation_id="corr-1",
    )
    
    events_received = []
    callbacks.register_listener(lambda e: events_received.append(e))
    
    callbacks.on_agent_message(
        task_id="task-1",
        agent_id="agent-1",
        message_type="proposal",
        message="Sending proposal",
        data={"proposal_id": "prop-123"},
    )
    
    assert len(events_received) == 1
    event = events_received[0]
    assert event.event_type == EventType.AGENT_MESSAGE
    assert event.data["message_type"] == "proposal"
