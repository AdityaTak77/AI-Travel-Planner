"""
Pydantic models for the AI Travel Planner system.

This module defines all data models used throughout the application including:
- TravelerProfile: user preferences and requirements
- Itinerary: complete travel plan with segments
- Offer: booking options from various providers
- MonitoringEvent: system observability events
- TaskContext: shared context between agents
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TravelerPreferences(BaseModel):
    """Travel preferences for personalization."""
    model_config = ConfigDict(json_encoders={Decimal: float})
    
    budget_min: Decimal = Field(description="Minimum budget in default currency")
    budget_max: Decimal = Field(description="Maximum budget in default currency")
    travel_style: str = Field(
        default="balanced",
        description="Travel style: budget, balanced, luxury"
    )
    interests: List[str] = Field(
        default_factory=list,
        description="List of interests (e.g., culture, adventure, food)"
    )
    accessibility_needs: List[str] = Field(
        default_factory=list,
        description="Special accessibility requirements"
    )
    dietary_restrictions: List[str] = Field(
        default_factory=list,
        description="Dietary restrictions or preferences"
    )


class TravelerProfile(BaseModel):
    """Complete traveler profile with identity and preferences."""
    
    traveler_id: str = Field(description="Unique traveler identifier")
    name: str = Field(description="Traveler name")
    email: Optional[str] = Field(default=None, description="Contact email")
    home_location: str = Field(description="Home city/country")
    preferences: TravelerPreferences = Field(description="Travel preferences")
    loyalty_programs: Dict[str, str] = Field(
        default_factory=dict,
        description="Loyalty program memberships {provider: member_id}"
    )


class Location(BaseModel):
    """Geographic location with coordinates."""
    
    name: str = Field(description="Location name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    timezone: Optional[str] = Field(default=None, description="Timezone identifier")


class PricingBreakdown(BaseModel):
    """Detailed pricing breakdown for an offer."""
    model_config = ConfigDict(json_encoders={Decimal: float})
    
    base_price: Decimal = Field(description="Base price before fees")
    taxes: Decimal = Field(default=Decimal("0.00"), description="Tax amount")
    fees: Decimal = Field(default=Decimal("0.00"), description="Service fees")
    total: Decimal = Field(description="Total price")
    currency: str = Field(default="USD", description="Currency code")
    
    @field_validator("total")
    @classmethod
    def validate_total(cls, v: Decimal, info: Any) -> Decimal:
        """Ensure total matches sum of components."""
        # Note: In Pydantic v2, validators receive info instead of values
        return v


class OfferType(str, Enum):
    """Types of travel offers."""
    
    FLIGHT = "flight"
    HOTEL = "hotel"
    ACTIVITY = "activity"
    TRANSPORT = "transport"
    PACKAGE = "package"


class Offer(BaseModel):
    """A bookable travel offer from a provider."""
    
    offer_id: str = Field(description="Unique offer identifier")
    offer_type: OfferType = Field(description="Type of offer")
    provider: str = Field(description="Provider name")
    title: str = Field(description="Offer title")
    description: Optional[str] = Field(default=None, description="Detailed description")
    pricing: PricingBreakdown = Field(description="Price breakdown")
    start_time: Optional[datetime] = Field(default=None, description="Start date/time")
    end_time: Optional[datetime] = Field(default=None, description="End date/time")
    location: Optional[Location] = Field(default=None, description="Offer location")
    capacity: Optional[int] = Field(default=None, description="Available capacity")
    rating: Optional[float] = Field(default=None, description="User rating (0-5)")
    amenities: List[str] = Field(default_factory=list, description="List of amenities")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific metadata"
    )


class ItinerarySegment(BaseModel):
    """A single segment in a travel itinerary."""
    
    segment_id: str = Field(description="Unique segment identifier")
    day: int = Field(description="Day number in itinerary (1-indexed)")
    start_time: datetime = Field(description="Segment start time")
    end_time: datetime = Field(description="Segment end time")
    segment_type: OfferType = Field(description="Type of segment")
    title: str = Field(description="Segment title")
    description: str = Field(description="Segment description")
    location: Location = Field(description="Segment location")
    offer: Optional[Offer] = Field(default=None, description="Associated booking offer")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    order: int = Field(description="Order within the day")


class Itinerary(BaseModel):
    """Complete travel itinerary with all segments."""
    
    itinerary_id: str = Field(description="Unique itinerary identifier")
    traveler_profile: TravelerProfile = Field(description="Traveler information")
    destination: str = Field(description="Primary destination")
    start_date: datetime = Field(description="Trip start date")
    end_date: datetime = Field(description="Trip end date")
    segments: List[ItinerarySegment] = Field(
        default_factory=list,
        description="List of itinerary segments"
    )
    total_cost: PricingBreakdown = Field(description="Total trip cost")
    optimization_notes: Optional[str] = Field(
        default=None,
        description="Notes on optimization applied"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    def to_markdown(self) -> str:
        """Export itinerary as human-readable Markdown."""
        lines = [
            f"# Travel Itinerary: {self.destination}",
            "",
            f"**Traveler:** {self.traveler_profile.name}",
            f"**Dates:** {self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}",
            f"**Total Cost:** {self.total_cost.currency} {self.total_cost.total}",
            "",
            "---",
            "",
        ]
        
        # Group segments by day
        segments_by_day: Dict[int, List[ItinerarySegment]] = {}
        for segment in sorted(self.segments, key=lambda s: (s.day, s.order)):
            if segment.day not in segments_by_day:
                segments_by_day[segment.day] = []
            segments_by_day[segment.day].append(segment)
        
        for day, day_segments in sorted(segments_by_day.items()):
            lines.append(f"## Day {day}")
            lines.append("")
            for seg in day_segments:
                lines.append(f"### {seg.start_time.strftime('%I:%M %p')} - {seg.title}")
                lines.append(f"**Location:** {seg.location.name}, {seg.location.city}")
                lines.append(f"**Duration:** {seg.start_time.strftime('%I:%M %p')} - {seg.end_time.strftime('%I:%M %p')}")
                lines.append("")
                lines.append(seg.description)
                if seg.offer:
                    lines.append(
                        f"\n**Cost:** {seg.offer.pricing.currency} {seg.offer.pricing.total}"
                    )
                if seg.notes:
                    lines.append(f"\n*Note: {seg.notes}*")
                lines.append("")
                lines.append("---")
                lines.append("")
        
        if self.optimization_notes:
            lines.append("## Optimization Notes")
            lines.append("")
            lines.append(self.optimization_notes)
            lines.append("")
        
        return "\n".join(lines)


class TaskStatus(str, Enum):
    """Task execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskContext(BaseModel):
    """Shared context passed between agents during task execution."""
    
    task_id: str = Field(description="Unique task identifier")
    correlation_id: str = Field(description="Correlation ID for tracing")
    trace_id: str = Field(description="Trace ID for distributed tracing")
    traveler_profile: TravelerProfile = Field(description="Traveler profile")
    request_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original request parameters"
    )
    intermediate_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from intermediate steps"
    )
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )


class EventType(str, Enum):
    """Monitoring event types."""
    
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_END = "task_end"
    TASK_ERROR = "task_error"
    STATE_CHANGE = "state_change"
    API_CALL = "api_call"
    AGENT_MESSAGE = "agent_message"


class EventSeverity(str, Enum):
    """Event severity levels."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitoringEvent(BaseModel):
    """Structured monitoring event for observability."""
    
    event_id: str = Field(description="Unique event identifier")
    event_type: EventType = Field(description="Type of event")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="Event severity")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )
    trace_id: str = Field(description="Trace ID for distributed tracing")
    correlation_id: str = Field(description="Correlation ID for request tracking")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    agent_id: Optional[str] = Field(default=None, description="Agent that generated event")
    message: str = Field(description="Event message")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event data"
    )
    error: Optional[Dict[str, str]] = Field(
        default=None,
        description="Error information if event_type is TASK_ERROR"
    )
    
    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSON logging."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
