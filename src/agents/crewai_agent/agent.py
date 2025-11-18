"""
CrewAI agent implementation skeleton.

This module provides a wrapper for CrewAI agent framework with
A2A protocol support, state management, and monitoring callbacks.
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.a2a.adapters.in_memory import get_a2a_adapter
from src.a2a.protocol import create_proposal_message
from src.callbacks.monitoring import MonitoringCallbacks
from src.models.itinerary import Offer, OfferType, PricingBreakdown, TaskContext, Location
from src.state.store import get_state_store
from src.logging.json_logger import get_logger
from src.integrations.groq_client import GroqClient
from src.agents.llm_prompts import build_planning_prompt

logger = get_logger(__name__)


class CrewAIAgent:
    """
    CrewAI agent wrapper for travel planning.
    
    This agent is responsible for:
    - Gathering travel requirements
    - Searching for options (flights, hotels, activities)
    - Creating initial travel proposals
    - Publishing proposals via A2A protocol
    
    NOTE: This is a skeleton implementation. In production:
    1. Install crewai package: pip install crewai
    2. Initialize actual CrewAI agent with roles and goals
    3. Implement real API calls to travel services
    """
    
    def __init__(
        self,
        agent_id: str = "crewai-planner",
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize CrewAI agent.
        
        Args:
            agent_id: Unique agent identifier
            api_key: CrewAI API key (optional)
        """
        self.agent_id = agent_id
        self.api_key = api_key
        
        # TODO: Initialize actual CrewAI agent
        # from crewai import Agent, Task, Crew
        # self._agent = Agent(
        #     role="Travel Planner",
        #     goal="Create optimal travel itineraries",
        #     backstory="Expert travel agent with years of experience",
        #     api_key=api_key,
        # )
        
        logger.info(f"CrewAI agent initialized: {agent_id}")
    
    async def plan_itinerary(
        self,
        context: TaskContext,
        callbacks: MonitoringCallbacks,
    ) -> Dict[str, Any]:
        """
        Plan a travel itinerary using Groq LLM based on context.
        
        Args:
            context: Task context with traveler profile and requirements
            callbacks: Monitoring callbacks
            
        Returns:
            Planning results with offers and proposal
        """
        callbacks.on_task_start(
            task_id=context.task_id,
            agent_id=self.agent_id,
            message=f"CrewAI agent started planning for {context.traveler_profile.name}",
        )
        
        try:
            # Step 1: Build comprehensive planning prompt
            callbacks.on_task_progress(
                task_id=context.task_id,
                progress=0.2,
                agent_id=self.agent_id,
                message="Building planning prompt with research data",
            )
            
            # Get research data from context
            research_data = context.intermediate_results.get("gemini_research", {})
            
            prompt = build_planning_prompt(
                profile=context.traveler_profile,
                request_params=context.request_params,
                research_data=research_data,
            )
            
            # Step 2: Call Groq LLM for itinerary generation
            callbacks.on_task_progress(
                task_id=context.task_id,
                progress=0.5,
                agent_id=self.agent_id,
                message="Generating itinerary with Groq AI (llama-3.3-70b-versatile)",
            )
            
            async with GroqClient() as groq:
                llm_response = await groq.chat(
                    prompt=prompt,
                    system_prompt="You are an expert travel planner. Generate detailed, realistic travel itineraries in JSON format only. Include accurate cost estimates, specific hotels, flights, and daily activities.",
                    temperature=0.7,
                    max_tokens=3000,
                )
            
            # Step 3: Parse LLM response
            callbacks.on_task_progress(
                task_id=context.task_id,
                progress=0.7,
                agent_id=self.agent_id,
                message="Parsing AI-generated itinerary",
            )
            
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_str = llm_response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.startswith("```"):
                    json_str = json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                json_str = json_str.strip()
                
                itinerary_data = json.loads(json_str)
                daily_schedule_count = len(itinerary_data.get('daily_schedule', []))
                logger.info(f"Successfully parsed LLM itinerary: {daily_schedule_count} days in daily_schedule")
                
                # Log structure for debugging
                if daily_schedule_count == 0:
                    logger.warning(f"LLM returned empty daily_schedule. Keys in response: {list(itinerary_data.keys())}")
                    logger.warning(f"Full response preview: {json.dumps(itinerary_data, indent=2)[:1000]}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"LLM Response: {llm_response[:500]}")
                # Fallback to basic structure
                itinerary_data = {
                    "destination": context.request_params.get("destination"),
                    "days": [],
                    "flights": [],
                    "hotels": [],
                    "total_cost": 0,
                }
            
            # Step 4: Convert to Offer objects for A2A protocol
            callbacks.on_task_progress(
                task_id=context.task_id,
                progress=0.9,
                agent_id=self.agent_id,
                message="Creating travel proposal",
            )
            
            # Extract transportation (flights/trains)
            transport_data = itinerary_data.get("transportation", {})
            flights = self._create_transport_offers(transport_data)
            
            # Extract accommodation
            accommodation_data = itinerary_data.get("accommodation", {})
            hotels = self._create_accommodation_offers(accommodation_data)
            
            # Extract daily activities
            daily_schedule = itinerary_data.get("daily_schedule", [])
            activities = self._create_activity_offers_from_schedule(daily_schedule)
            
            # Store in state
            state_store = await get_state_store()
            await state_store.set(f"llm_itinerary:{context.task_id}", itinerary_data, ttl=3600)
            await state_store.set(f"flights:{context.task_id}", flights, ttl=3600)
            await state_store.set(f"hotels:{context.task_id}", hotels, ttl=3600)
            await state_store.set(f"activities:{context.task_id}", activities, ttl=3600)
            
            # Step 5: Create A2A proposal
            cost_breakdown = itinerary_data.get("cost_breakdown", {})
            proposal_data = {
                "destination": itinerary_data.get("destination"),
                "daily_schedule": daily_schedule,
                "flights": [self._offer_to_dict(f) for f in flights],
                "hotels": [self._offer_to_dict(h) for h in hotels],
                "activities": [self._offer_to_dict(a) for a in activities],
                "estimated_total": str(cost_breakdown.get("total", 0)),
                "currency": cost_breakdown.get("currency", "INR"),
                "cost_breakdown": cost_breakdown,
                "budget_max": float(context.traveler_profile.preferences.budget_max),
                "budget_min": float(context.traveler_profile.preferences.budget_min),
            }
            
            # Send A2A proposal message
            a2a_adapter = get_a2a_adapter()
            proposal_msg = create_proposal_message(
                proposal_data=proposal_data,
                trace_id=context.trace_id,
                correlation_id=context.correlation_id,
                sender=self.agent_id,
                receiver="adk-optimizer",
            )
            
            await a2a_adapter.send_message(proposal_msg)
            
            callbacks.on_agent_message(
                task_id=context.task_id,
                agent_id=self.agent_id,
                message_type="proposal",
                message=f"Sent AI-generated proposal to ADK optimizer",
                data={"message_id": proposal_msg.message_id, "days": len(itinerary_data.get("days", []))},
            )
            
            callbacks.on_task_end(
                task_id=context.task_id,
                agent_id=self.agent_id,
                message="CrewAI agent completed AI-powered planning",
                data={"proposal_id": proposal_msg.message_id, "total_cost": itinerary_data.get("total_cost")},
            )
            
            return {
                "proposal_message": proposal_msg,
                "flights": flights,
                "hotels": hotels,
                "activities": activities,
                "itinerary_data": itinerary_data,
            }
            
        except Exception as e:
            callbacks.on_task_error(
                task_id=context.task_id,
                error=e,
                agent_id=self.agent_id,
                message=f"Error in CrewAI planning: {str(e)}",
            )
            raise
    
    def _create_transport_offers(self, transport_data: Dict[str, Any]) -> List[Offer]:
        """Convert LLM transportation data to Offer objects."""
        offers = []
        if not transport_data:
            return offers
            
        to_dest = transport_data.get("to_destination", {})
        if to_dest:
            try:
                cost = to_dest.get("cost", 0)
                offers.append(Offer(
                    offer_id=f"transport-{uuid.uuid4().hex[:8]}",
                    offer_type=OfferType.FLIGHT,
                    provider=to_dest.get("method", "Transport"),
                    title=to_dest.get("method", "Transportation to destination"),
                    description=f"Duration: {to_dest.get('duration', 'N/A')}",
                    pricing=PricingBreakdown(
                        base_price=Decimal(str(cost)),
                        taxes=Decimal("0"),
                        fees=Decimal("0"),
                        total=Decimal(str(cost)),
                        currency="INR",
                    ),
                    start_time=datetime.utcnow(),
                    location=Location(
                        name="Destination",
                        city="Destination",
                        country="",
                    ),
                    rating=4.0,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse transport offer: {e}")
        return offers
    
    def _create_accommodation_offers(self, accommodation_data: Dict[str, Any]) -> List[Offer]:
        """Convert LLM accommodation data to Offer objects."""
        offers = []
        if not accommodation_data:
            return offers
            
        try:
            total_cost = accommodation_data.get("total_cost", 0)
            cost_per_night = accommodation_data.get("cost_per_night", 0)
            offers.append(Offer(
                offer_id=f"hotel-{uuid.uuid4().hex[:8]}",
                offer_type=OfferType.HOTEL,
                provider=accommodation_data.get("name", "Hotel"),
                title=accommodation_data.get("name", "Accommodation"),
                description=accommodation_data.get("recommendation", ""),
                pricing=PricingBreakdown(
                    base_price=Decimal(str(cost_per_night)),
                    taxes=Decimal("0"),
                    fees=Decimal("0"),
                    total=Decimal(str(total_cost)),
                    currency="INR",
                ),
                location=Location(
                    name=accommodation_data.get("name", ""),
                    city="",
                    country="",
                ),
                rating=4.0,
                amenities=[],
            ))
        except Exception as e:
            logger.warning(f"Failed to parse accommodation offer: {e}")
        return offers
    
    def _create_activity_offers_from_schedule(self, daily_schedule: List[Dict[str, Any]]) -> List[Offer]:
        """Convert LLM daily activities to Offer objects."""
        offers = []
        for day in daily_schedule:
            for activity in day.get("activities", []):
                try:
                    cost = activity.get("cost", 0)
                    offers.append(Offer(
                        offer_id=f"activity-{uuid.uuid4().hex[:8]}",
                        offer_type=OfferType.ACTIVITY,
                        provider=activity.get("location", "Local Activity"),
                        title=activity.get("name", "Activity"),
                        description=f"{activity.get('time', '')}: {activity.get('description', '')}",
                        pricing=PricingBreakdown(
                            base_price=Decimal(str(cost)),
                            taxes=Decimal("0"),
                            fees=Decimal("0"),
                            total=Decimal(str(cost)),
                            currency="INR",
                        ),
                        location=Location(
                            name=activity.get("location", ""),
                            city=activity.get("location", ""),
                            country="",
                        ),
                        rating=4.5,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse activity offer: {e}")
        return offers
    
    async def _search_flights(
        self,
        origin: str,
        destination: str,
        start_date: str,
        end_date: str,
    ) -> List[Offer]:
        """Search for flight options (stub implementation - now replaced by LLM)."""
        # TODO: Integrate with real flight search API
        logger.info(f"Searching flights: {origin} -> {destination}")
        
        return [
            Offer(
                offer_id=f"flight-{uuid.uuid4().hex[:8]}",
                offer_type=OfferType.FLIGHT,
                provider="SkyAirlines",
                title=f"{origin} to {destination}",
                description="Direct flight with 1 checked bag included",
                pricing=PricingBreakdown(
                    base_price=Decimal("450.00"),
                    taxes=Decimal("75.50"),
                    fees=Decimal("25.00"),
                    total=Decimal("550.50"),
                    currency="USD",
                ),
                start_time=datetime.fromisoformat(start_date) if start_date else datetime.utcnow(),
                location=Location(name=destination, city=destination, country=""),
                rating=4.2,
            )
        ]
    
    async def _search_hotels(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        budget: Decimal,
    ) -> List[Offer]:
        """Search for hotel options (stub implementation)."""
        # TODO: Integrate with real hotel search API
        logger.info(f"Searching hotels in {destination}")
        
        return [
            Offer(
                offer_id=f"hotel-{uuid.uuid4().hex[:8]}",
                offer_type=OfferType.HOTEL,
                provider="HotelBooking",
                title=f"Downtown Hotel - {destination}",
                description="Modern hotel in city center with breakfast included",
                pricing=PricingBreakdown(
                    base_price=Decimal("150.00"),
                    taxes=Decimal("22.50"),
                    fees=Decimal("12.00"),
                    total=Decimal("184.50"),
                    currency="USD",
                ),
                location=Location(name=destination, city=destination, country=""),
                rating=4.5,
                amenities=["WiFi", "Breakfast", "Pool", "Gym"],
            )
        ]
    
    async def _search_activities(
        self,
        destination: str,
        interests: List[str],
    ) -> List[Offer]:
        """Search for activities (stub implementation)."""
        # TODO: Integrate with real activity search API
        logger.info(f"Searching activities in {destination}")
        
        return [
            Offer(
                offer_id=f"activity-{uuid.uuid4().hex[:8]}",
                offer_type=OfferType.ACTIVITY,
                provider="LocalTours",
                title=f"City Walking Tour - {destination}",
                description="3-hour guided walking tour of historic sites",
                pricing=PricingBreakdown(
                    base_price=Decimal("45.00"),
                    taxes=Decimal("3.60"),
                    fees=Decimal("2.40"),
                    total=Decimal("51.00"),
                    currency="USD",
                ),
                location=Location(name=destination, city=destination, country=""),
                rating=4.8,
            )
        ]
    
    def _offer_to_dict(self, offer: Offer) -> Dict[str, Any]:
        """Convert Offer to dictionary."""
        return offer.model_dump()
    
    def _calculate_total(self, offers: List[Offer]) -> Decimal:
        """Calculate total cost from offers."""
        return sum(offer.pricing.total for offer in offers)
