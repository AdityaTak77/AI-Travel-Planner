"""
Logger adapter for monitoring events.

Forwards MonitoringEvent instances to structured logger for persistence.
"""

import json
from typing import Optional, TextIO

from src.models.itinerary import MonitoringEvent
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class MonitoringLoggerAdapter:
    """
    Adapter that forwards monitoring events to structured logger.
    
    This adapter can write events to console, files, or external systems.
    """
    
    def __init__(self, log_file: Optional[str] = None) -> None:
        """
        Initialize logger adapter.
        
        Args:
            log_file: Optional file path to write events (in addition to console)
        """
        self.log_file = log_file
        self._file_handle: Optional[TextIO] = None
        
        if log_file:
            try:
                self._file_handle = open(log_file, "a", encoding="utf-8")
                logger.info(f"Monitoring events will be written to {log_file}")
            except Exception as e:
                logger.error(f"Failed to open monitoring log file: {e}")
    
    def log_event(self, event: MonitoringEvent) -> None:
        """
        Log a monitoring event.
        
        Args:
            event: MonitoringEvent to log
        """
        # Convert to log dictionary
        log_dict = event.to_log_dict()
        
        # Prepare safe extras for logging (avoid reserved LogRecord keys)
        safe_extra = {"monitoring_event": True}
        # Rename any reserved keys if present to avoid collisions
        reserved_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName", "processName",
            "process", "message", "asctime",
        }
        for k, v in log_dict.items():
            if k in reserved_keys:
                safe_extra[f"event_{k}"] = v
            else:
                safe_extra[k] = v
        
        # Write to console via structured logger
        log_level = self._get_log_level(event.severity.value)
        logger.log(
            log_level,
            event.message,
            extra=safe_extra,
        )
        
        # Write to file if configured
        if self._file_handle:
            try:
                json_line = json.dumps(log_dict) + "\n"
                self._file_handle.write(json_line)
                self._file_handle.flush()
            except Exception as e:
                logger.error(f"Failed to write monitoring event to file: {e}")
    
    def _get_log_level(self, severity: str) -> int:
        """
        Map event severity to logging level.
        
        Args:
            severity: Event severity string
            
        Returns:
            Logging level constant
        """
        import logging
        
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return mapping.get(severity.lower(), logging.INFO)
    
    def close(self) -> None:
        """Close file handle if open."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def __enter__(self) -> "MonitoringLoggerAdapter":
        """Context manager entry."""
        return self
    
    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()


def create_monitoring_listener(log_file: Optional[str] = None) -> tuple:
    """
    Create a monitoring listener function and adapter.
    
    Args:
        log_file: Optional file path for event logs
        
    Returns:
        Tuple of (listener_function, adapter_instance)
    """
    adapter = MonitoringLoggerAdapter(log_file)
    
    def listener(event: MonitoringEvent) -> None:
        """Listener function that forwards events to adapter."""
        adapter.log_event(event)
    
    return listener, adapter
