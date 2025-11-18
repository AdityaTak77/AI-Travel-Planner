"""
Main entry point for AI Travel Planner.

This module provides the CLI interface and orchestrates the entire
travel planning workflow with monitoring and A2A coordination.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.callbacks.logger_adapter import create_monitoring_listener
from src.callbacks.monitoring import MonitoringCallbacks
from src.config.settings import get_settings
from src.models.itinerary import TravelerPreferences, TravelerProfile
from src.workflows.dynamic_planner import DynamicPlannerWorkflow
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


async def run_planning_workflow(input_file: str) -> None:
    """
    Run the travel planning workflow from an input file.
    
    Args:
        input_file: Path to JSON input file with request
    """
    settings = get_settings()
    
    # Load input request
    logger.info(f"Loading request from {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        request_data = json.load(f)
    
    # Create traveler profile
    traveler_data = request_data.get("traveler", {})
    preferences_data = traveler_data.get("preferences", {})
    
    traveler_profile = TravelerProfile(
        traveler_id=traveler_data.get("traveler_id", str(uuid.uuid4())),
        name=traveler_data.get("name", "Anonymous"),
        email=traveler_data.get("email"),
        home_location=traveler_data.get("home_location", "Unknown"),
        preferences=TravelerPreferences(
            budget_min=preferences_data.get("budget_min", 500),
            budget_max=preferences_data.get("budget_max", 2000),
            travel_style=preferences_data.get("travel_style", "balanced"),
            interests=preferences_data.get("interests", []),
            accessibility_needs=preferences_data.get("accessibility_needs", []),
            dietary_restrictions=preferences_data.get("dietary_restrictions", []),
        ),
        loyalty_programs=traveler_data.get("loyalty_programs", {}),
    )
    
    # Extract request parameters
    request_params = request_data.get("request", {})
    
    # Create monitoring context
    trace_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    
    callbacks = MonitoringCallbacks(
        trace_id=trace_id,
        correlation_id=correlation_id,
    )
    
    # Register logging listener
    if settings.enable_monitoring:
        listener, adapter = create_monitoring_listener(
            log_file="monitoring_events.json"
        )
        callbacks.register_listener(listener)
    
    logger.info(
        f"Starting travel planning for {traveler_profile.name}",
        extra={
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "destination": request_params.get("destination"),
        }
    )
    
    # Execute workflow
    workflow = DynamicPlannerWorkflow()
    itinerary = await workflow.execute(
        traveler_profile=traveler_profile,
        request_params=request_params,
        callbacks=callbacks,
    )
    
    # Output results
    print("\n" + "=" * 80)
    print("TRAVEL ITINERARY GENERATED")
    print("=" * 80)
    
    # JSON output
    json_output = itinerary.model_dump_json(indent=2)
    print("\nJSON OUTPUT:")
    print(json_output)
    
    # Save JSON to file
    output_json_path = Path("examples") / "generated_itinerary.json"
    output_json_path.parent.mkdir(exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"\nJSON saved to: {output_json_path}")
    
    # Markdown output
    markdown_output = itinerary.to_markdown()
    print("\n" + "=" * 80)
    print("MARKDOWN OUTPUT:")
    print("=" * 80)
    print(markdown_output)
    
    # Save Markdown to file
    output_md_path = Path("examples") / "generated_itinerary.md"
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_output)
    print(f"\nMarkdown saved to: {output_md_path}")
    
    logger.info(
        "Planning workflow completed",
        extra={
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "itinerary_id": itinerary.itinerary_id,
        }
    )


def main() -> None:
    """Main entry point."""
    # Load settings
    settings = get_settings()
    
    print(f"AI Travel Planner v0.1.0")
    print(f"Environment: {settings.app_env}")
    print(f"Log Level: {settings.log_level}")
    print(f"State Backend: {settings.state_backend}")
    print(f"Allow Booking: {settings.allow_booking_operations}")
    print()
    
    # Check for input file argument
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <input_request_json>")
        print()
        print("Example:")
        print("  python -m src.main examples/sample_itinerary_request.json")
        print()
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Run async workflow
    try:
        asyncio.run(run_planning_workflow(input_file))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
