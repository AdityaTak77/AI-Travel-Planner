"""
Unit tests for Pydantic models.

Tests model validation, serialization, and Markdown export.
"""

import json
from datetime import datetime
from decimal import Decimal

import pytest

from src.models.itinerary import (
    Itinerary,
    ItinerarySegment,
    Location,
    Offer,
    OfferType,
    PricingBreakdown,
    TravelerPreferences,
    TravelerProfile,
    MonitoringEvent,
    EventType,
    EventSeverity,
)


def test_traveler_profile_validation() -> None:
    """Test TravelerProfile model validation."""
    profile = TravelerProfile(
        traveler_id="test-123",
        name="John Doe",
        email="john@example.com",
        home_location="New York",
        preferences=TravelerPreferences(
            budget_min=Decimal("1000"),
            budget_max=Decimal("5000"),
            travel_style="luxury",
            interests=["culture", "food"],
        ),
    )
    
    assert profile.traveler_id == "test-123"
    assert profile.name == "John Doe"
    assert profile.preferences.budget_max == Decimal("5000")


def test_pricing_breakdown() -> None:
    """Test PricingBreakdown model."""
    pricing = PricingBreakdown(
        base_price=Decimal("100.00"),
        taxes=Decimal("15.00"),
        fees=Decimal("5.00"),
        total=Decimal("120.00"),
        currency="USD",
    )
    
    assert pricing.total == Decimal("120.00")
    assert pricing.currency == "USD"


def test_offer_serialization() -> None:
    """Test Offer model serialization."""
    offer = Offer(
        offer_id="offer-123",
        offer_type=OfferType.FLIGHT,
        provider="TestAirline",
        title="Test Flight",
        description="Direct flight",
        pricing=PricingBreakdown(
            base_price=Decimal("400.00"),
            taxes=Decimal("60.00"),
            fees=Decimal("20.00"),
            total=Decimal("480.00"),
        ),
        location=Location(name="Paris", city="Paris", country="France"),
        rating=4.5,
    )
    
    # Serialize to JSON
    json_str = offer.model_dump_json()
    data = json.loads(json_str)
    
    assert data["offer_id"] == "offer-123"
    assert data["offer_type"] == "flight"
    assert data["provider"] == "TestAirline"
    
    # Deserialize back
    offer2 = Offer(**data)
    assert offer2.offer_id == offer.offer_id


def test_itinerary_creation() -> None:
    """Test Itinerary model creation."""
    profile = TravelerProfile(
        traveler_id="test-456",
        name="Jane Smith",
        home_location="London",
        preferences=TravelerPreferences(
            budget_min=Decimal("500"),
            budget_max=Decimal("2000"),
        ),
    )
    
    segment = ItinerarySegment(
        segment_id="seg-1",
        day=1,
        start_time=datetime(2025, 12, 1, 10, 0),
        end_time=datetime(2025, 12, 1, 14, 0),
        segment_type=OfferType.ACTIVITY,
        title="City Tour",
        description="Guided city tour",
        location=Location(name="Paris", city="Paris", country="France"),
        order=0,
    )
    
    itinerary = Itinerary(
        itinerary_id="itin-789",
        traveler_profile=profile,
        destination="Paris",
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 5),
        segments=[segment],
        total_cost=PricingBreakdown(
            base_price=Decimal("1500"),
            taxes=Decimal("150"),
            fees=Decimal("50"),
            total=Decimal("1700"),
        ),
    )
    
    assert itinerary.itinerary_id == "itin-789"
    assert len(itinerary.segments) == 1
    assert itinerary.total_cost.total == Decimal("1700")


def test_itinerary_markdown_export() -> None:
    """Test Itinerary Markdown export."""
    profile = TravelerProfile(
        traveler_id="test-md",
        name="Test User",
        home_location="NYC",
        preferences=TravelerPreferences(
            budget_min=Decimal("1000"),
            budget_max=Decimal("3000"),
        ),
    )
    
    itinerary = Itinerary(
        itinerary_id="itin-md",
        traveler_profile=profile,
        destination="Tokyo",
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 5),
        segments=[],
        total_cost=PricingBreakdown(
            base_price=Decimal("2000"),
            taxes=Decimal("200"),
            fees=Decimal("50"),
            total=Decimal("2250"),
        ),
    )
    
    markdown = itinerary.to_markdown()
    
    assert "# Travel Itinerary: Tokyo" in markdown
    assert "Test User" in markdown
    assert "USD 2250" in markdown


def test_monitoring_event() -> None:
    """Test MonitoringEvent model."""
    event = MonitoringEvent(
        event_id="evt-123",
        event_type=EventType.TASK_START,
        severity=EventSeverity.INFO,
        trace_id="trace-abc",
        correlation_id="corr-xyz",
        task_id="task-001",
        agent_id="test-agent",
        message="Test event",
        data={"key": "value"},
    )
    
    assert event.event_type == EventType.TASK_START
    assert event.severity == EventSeverity.INFO
    
    # Test to_log_dict
    log_dict = event.to_log_dict()
    assert log_dict["event_id"] == "evt-123"
    assert log_dict["event_type"] == "task_start"
    assert log_dict["message"] == "Test event"


def test_json_roundtrip() -> None:
    """Test JSON serialization round-trip."""
    original = Offer(
        offer_id="test-roundtrip",
        offer_type=OfferType.HOTEL,
        provider="TestHotel",
        title="Test Hotel",
        pricing=PricingBreakdown(
            base_price=Decimal("150"),
            taxes=Decimal("15"),
            fees=Decimal("5"),
            total=Decimal("170"),
        ),
    )
    
    # Serialize
    json_str = original.model_dump_json()
    
    # Deserialize
    data = json.loads(json_str)
    restored = Offer(**data)
    
    assert restored.offer_id == original.offer_id
    assert restored.offer_type == original.offer_type
    assert restored.pricing.total == original.pricing.total
