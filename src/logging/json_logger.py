"""
Structured JSON logger with correlation ID support.

Provides structured logging capabilities for observability and debugging.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from src.config.settings import get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields from record
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        
        # Add any other extra attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
                "trace_id", "correlation_id", "task_id", "agent_id",
            ]:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    
    # Optional: File handler for monitoring events
    # TODO: Add file rotation using RotatingFileHandler
    # file_handler = logging.FileHandler("monitoring_events.json")
    # file_handler.setFormatter(StructuredFormatter())
    # logger.addHandler(file_handler)
    
    return logger


class CorrelationAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds correlation context.
    
    Usage:
        logger = CorrelationAdapter(
            get_logger(__name__),
            {"trace_id": trace_id, "correlation_id": corr_id}
        )
        logger.info("Message")  # Automatically includes trace_id and correlation_id
    """
    
    def process(self, msg: str, kwargs: Any) -> tuple:
        """Add correlation context to log records."""
        # Merge extra context
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs
