"""
Dynamic travel planner workflow orchestration.

Orchestrates the multi-agent travel planning workflow including:
- Parallel data fetching
- Agent coordination via A2A protocol
- Budget constraint application
- Final itinerary generation
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from src.a2a.adapters.in_memory import get_a2a_adapter
from src.a2a.protocol import A2AMessageType
from src.agents.adk_agent.agent import ADKAgent
from src.agents.crewai_agent.agent import CrewAIAgent
from src.callbacks.monitoring import MonitoringCallbacks
from src.models.itinerary import (
    Itinerary,
    ItinerarySegment,
    Location,
    Offer,
    OfferType,
    PricingBreakdown,
    TaskContext,
    TaskStatus,
    TravelerProfile,
)
from src.state.store import get_state_store
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class DynamicPlannerWorkflow:
    """
    Orchestrates the dynamic travel planning workflow.
    
    This workflow coordinates multiple agents and external services
    to create optimized travel itineraries.
    """
    
    def __init__(self) -> None:
        """Initialize the workflow."""
        self.crewai_agent = CrewAIAgent()
        self.adk_agent = ADKAgent()
    
    async def execute(
        self,
        traveler_profile: TravelerProfile,
        request_params: Dict[str, Any],
        callbacks: MonitoringCallbacks,
    ) -> Itinerary:
        """
        Execute the planning workflow.
        
        Args:
            traveler_profile: Traveler profile and preferences
            request_params: Request parameters (destination, dates, etc.)
            callbacks: Monitoring callbacks
            
        Returns:
            Complete itinerary
        """
        # Create task context
        task_id = str(uuid.uuid4())
        context = TaskContext(
            task_id=task_id,
            correlation_id=callbacks.correlation_id,
            trace_id=callbacks.trace_id,
            traveler_profile=traveler_profile,
            request_params=request_params,
            status=TaskStatus.RUNNING,
        )
        
        logger.info(
            f"Starting planning workflow for {traveler_profile.name}",
            extra={
                "task_id": task_id,
                "trace_id": context.trace_id,
                "correlation_id": context.correlation_id,
            }
        )
        
        callbacks.on_task_start(
            task_id=task_id,
            message="Starting dynamic planning workflow",
            data={"destination": request_params.get("destination")},
        )
        
        try:
            # Step 1: Start ADK agent listener
            await self.adk_agent.start_listening(callbacks)
            
            # Step 2: CrewAI agent creates initial proposal
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.3,
                message="CrewAI agent creating travel proposal",
            )
            
            proposal_result = await self.crewai_agent.plan_itinerary(context, callbacks)
            
            # Step 3: Wait for ADK optimization response
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.6,
                message="Waiting for ADK agent optimization",
            )
            
            optimized_plan = await self._wait_for_optimization(
                context=context,
                timeout=30.0,
            )
            
            # Step 4: Assemble final itinerary
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.8,
                message="Assembling final itinerary",
            )
            
            itinerary = await self._create_itinerary(
                context=context,
                optimized_plan=optimized_plan,
                callbacks=callbacks,
            )
            
            # Update context status
            context.status = TaskStatus.COMPLETED
            
            callbacks.on_task_end(
                task_id=task_id,
                message="Workflow completed successfully",
                data={
                    "itinerary_id": itinerary.itinerary_id,
                    "total_cost": str(itinerary.total_cost.total),
                },
            )
            
            return itinerary
            
        except Exception as e:
            context.status = TaskStatus.FAILED
            callbacks.on_task_error(
                task_id=task_id,
                error=e,
                message=f"Workflow failed: {str(e)}",
            )
            raise

    def _parse_time_range(self, time_str: str, base_date: datetime) -> tuple[datetime, datetime]:
        """Parse a time range string like '9:00 AM - 11:00 AM' into start/end datetimes.

        Falls back to base_date 09:00-10:00 if parsing fails.
        """
        try:
            if not time_str or "-" not in time_str:
                return base_date.replace(hour=9, minute=0), base_date.replace(hour=10, minute=0)
            parts = [p.strip() for p in time_str.split("-")]
            if len(parts) != 2:
                return base_date.replace(hour=9, minute=0), base_date.replace(hour=10, minute=0)
            from datetime import datetime as dtmod
            start_raw, end_raw = parts
            start_dt = dtmod.strptime(start_raw, "%I:%M %p")
            end_dt = dtmod.strptime(end_raw, "%I:%M %p")
            start_full = base_date.replace(hour=start_dt.hour, minute=start_dt.minute, second=0, microsecond=0)
            end_full = base_date.replace(hour=end_dt.hour, minute=end_dt.minute, second=0, microsecond=0)
            # Ensure end after start
            if end_full <= start_full:
                end_full = start_full + timedelta(hours=1)
            return start_full, end_full
        except Exception:
            return base_date.replace(hour=9, minute=0), base_date.replace(hour=10, minute=0)
    
    async def _wait_for_optimization(
        self,
        context: TaskContext,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Wait for optimization response from ADK agent.
        
        Args:
            context: Task context
            timeout: Timeout in seconds
            
        Returns:
            Optimized plan data
        """
        a2a_adapter = get_a2a_adapter()
        
        # Wait for optimized_plan message
        message = await a2a_adapter.receive_message(
                agent_id="orchestrator",
                timeout=timeout,
                message_type=A2AMessageType.OPTIMIZED_PLAN,
            )
        
        if message:
            logger.info(f"Received optimized plan: {message.message_id}")
            return message.payload
        else:
            # Timeout - use original proposal
            logger.warning("Optimization timeout - using original proposal")
            state_store = await get_state_store()
            
            # Fallback to state store
            optimized = await state_store.get(f"optimized_plan:{context.task_id}")
            if not optimized:
                # Try correlation_id key used by ADK agent
                optimized = await state_store.get(f"optimized_plan:{context.correlation_id}")
            if optimized:
                return optimized
            
            # Final fallback - return empty optimization
            return {"flights": [], "hotels": [], "activities": []}
    
    async def _create_itinerary(
        self,
        context: TaskContext,
        optimized_plan: Dict[str, Any],
        callbacks: MonitoringCallbacks,
    ) -> Itinerary:
        """
        Create final itinerary from optimized plan.
        
        Args:
            context: Task context
            optimized_plan: Optimized plan data
            callbacks: Monitoring callbacks
            
        Returns:
            Complete itinerary
        """
        destination = context.request_params.get("destination", "Unknown")
        start_date = datetime.fromisoformat(
            context.request_params.get("start_date", datetime.utcnow().isoformat())
        )
        end_date = datetime.fromisoformat(
            context.request_params.get("end_date", datetime.utcnow().isoformat())
        )
        
        # Build segments from optimized offers AND daily schedule
        segments: List[ItinerarySegment] = []
        order = 0
        
        # Add flight segments
        for flight_data in optimized_plan.get("flights", []):
            flight = Offer(**flight_data)
            segments.append(
                ItinerarySegment(
                    segment_id=f"seg-{uuid.uuid4().hex[:8]}",
                    day=1,
                    start_time=flight.start_time or start_date,
                    end_time=flight.end_time or start_date,
                    segment_type=OfferType.FLIGHT,
                    title=flight.title,
                    description=flight.description or "",
                    location=flight.location or Location(
                        name=destination,
                        city=destination,
                        country="",
                    ),
                    offer=flight,
                    order=order,
                )
            )
            order += 1
        
        # Add hotel segments
        for hotel_data in optimized_plan.get("hotels", []):
            hotel = Offer(**hotel_data)
            segments.append(
                ItinerarySegment(
                    segment_id=f"seg-{uuid.uuid4().hex[:8]}",
                    day=1,
                    start_time=start_date,
                    end_time=end_date,
                    segment_type=OfferType.HOTEL,
                    title=hotel.title,
                    description=hotel.description or "",
                    location=hotel.location or Location(
                        name=destination,
                        city=destination,
                        country="",
                    ),
                    offer=hotel,
                    order=order,
                )
            )
            order += 1
        
        # Add daily schedule activities as segments
        daily_schedule = optimized_plan.get("daily_schedule", [])
        for day_data in daily_schedule:
            day_num = day_data.get("day", 1)
            base_date = start_date + timedelta(days=day_num - 1)

            # Add each activity as a segment with parsed times
            for activity in day_data.get("activities", []):
                try:
                    cost = activity.get("cost", 0)
                    time_range = activity.get("time", "")
                    start_dt, end_dt = self._parse_time_range(time_range, base_date)

                    activity_offer = Offer(
                        offer_id=f"activity-{uuid.uuid4().hex[:8]}",
                        offer_type=OfferType.ACTIVITY,
                        provider=activity.get("location", "Local"),
                        title=activity.get("name", "Activity"),
                        description=activity.get("description", ""),
                        pricing=PricingBreakdown(
                            base_price=Decimal(str(cost)),
                            taxes=Decimal("0"),
                            fees=Decimal("0"),
                            total=Decimal(str(cost)),
                            currency="INR",
                        ),
                        location=Location(
                            name=activity.get("location", destination),
                            city=destination,
                            country="",
                        ),
                        rating=4.5,
                    )

                    segments.append(
                        ItinerarySegment(
                            segment_id=f"seg-{uuid.uuid4().hex[:8]}",
                            day=day_num,
                            start_time=start_dt,
                            end_time=end_dt,
                            segment_type=OfferType.ACTIVITY,
                            title=activity.get("name", "Activity"),
                            description=activity.get("description", ""),
                            location=Location(
                                name=activity.get("location", destination),
                                city=destination,
                                country="",
                            ),
                            offer=activity_offer,
                            order=order,
                        )
                    )
                    order += 1
                except Exception as e:
                    logger.warning(f"Failed to create activity segment: {e}")
        
        # Calculate total cost from segments and cost breakdown
        cost_breakdown = optimized_plan.get("cost_breakdown", {})
        if cost_breakdown and cost_breakdown.get("total"):
            # Use LLM-provided cost breakdown
            total_cost = Decimal(str(cost_breakdown.get("total", 0)))
            currency = cost_breakdown.get("currency", "INR")
        else:
            # Fallback: calculate from segments
            total_cost = sum(
                seg.offer.pricing.total
                for seg in segments
                if seg.offer
            )
            currency = "USD"
        
        itinerary = Itinerary(
            itinerary_id=f"itin-{uuid.uuid4().hex[:8]}",
            traveler_profile=context.traveler_profile,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            segments=segments,
            total_cost=PricingBreakdown(
                base_price=total_cost * Decimal("0.85"),
                taxes=total_cost * Decimal("0.10"),
                fees=total_cost * Decimal("0.05"),
                total=total_cost,
                currency=currency,
            ),
            optimization_notes="\n".join(
                optimized_plan.get("optimization_applied", [])
            ),
        )
        
        return itinerary
