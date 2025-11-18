"""
ADK (Agent Development Kit) agent implementation skeleton.

This module provides a wrapper for ADK framework with A2A protocol support.
The ADK agent optimizes proposals received from other agents.
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.a2a.adapters.in_memory import get_a2a_adapter
from src.a2a.protocol import A2AMessage, A2AMessageType, create_optimized_plan_message
from src.callbacks.monitoring import MonitoringCallbacks
from src.models.itinerary import Offer, TaskContext
from src.state.store import get_state_store
from src.integrations.calculator import BudgetCalculator
from src.integrations.groq_client import GroqClient
from src.agents.llm_prompts import build_optimization_prompt
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class ADKAgent:
    """
    ADK agent wrapper for itinerary optimization.
    
    This agent is responsible for:
    - Receiving proposals via A2A protocol
    - Optimizing itineraries for cost, time, and preferences
    - Applying budget constraints
    - Returning optimized plans
    
    NOTE: This is a skeleton implementation. In production:
    1. Install ADK package if available
    2. Implement actual optimization algorithms
    3. Integrate with pricing and availability APIs
    """
    
    def __init__(
        self,
        agent_id: str = "adk-optimizer",
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize ADK agent.
        
        Args:
            agent_id: Unique agent identifier
            api_key: ADK API key (optional)
        """
        self.agent_id = agent_id
        self.api_key = api_key
        self._calculator = BudgetCalculator()
        
        # TODO: Initialize actual ADK agent
        # from adk import Agent
        # self._agent = Agent(
        #     name="Itinerary Optimizer",
        #     capabilities=["optimization", "budget_analysis"],
        #     api_key=api_key,
        # )
        
        logger.info(f"ADK agent initialized: {agent_id}")
    
    async def start_listening(self, callbacks: MonitoringCallbacks) -> None:
        """
        Start listening for A2A messages.
        
        Args:
            callbacks: Monitoring callbacks
        """
        a2a_adapter = get_a2a_adapter()
        
        def message_handler(message: A2AMessage) -> None:
            """Handle incoming A2A messages."""
            logger.info(
                f"ADK agent received message: {message.message_type}",
                extra={
                    "message_id": message.message_id,
                    "trace_id": message.trace_id,
                }
            )
            
            if message.message_type == A2AMessageType.PROPOSAL:
                # Handle proposal asynchronously
                import asyncio
                asyncio.create_task(
                    self.optimize_proposal(message, callbacks)
                )
        
        await a2a_adapter.subscribe(self.agent_id, message_handler)
        logger.info(f"ADK agent listening for messages")
    
    async def optimize_proposal(
        self,
        proposal_msg: A2AMessage,
        callbacks: MonitoringCallbacks,
    ) -> Dict[str, Any]:
        """
        Optimize a travel proposal.
        
        Args:
            proposal_msg: A2A proposal message
            callbacks: Monitoring callbacks
            
        Returns:
            Optimized plan data
        """
        task_id = proposal_msg.correlation_id
        
        callbacks.on_task_start(
            task_id=task_id,
            agent_id=self.agent_id,
            message=f"ADK agent started optimization",
        )
        
        try:
            proposal_data = proposal_msg.payload
            
            # Step 1: Load context from state
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.2,
                agent_id=self.agent_id,
                message="Loading proposal data",
            )
            
            state_store = await get_state_store()
            
            # Step 2: Analyze budget constraints
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.4,
                agent_id=self.agent_id,
                message="Analyzing budget constraints",
            )
            
            estimated_total = Decimal(proposal_data.get("estimated_total", "0"))
            
            # Step 3: Optimize offers
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.6,
                agent_id=self.agent_id,
                message="Optimizing travel options",
            )
            
            optimized = await self._apply_optimization(proposal_data)
            
            # Step 4: Validate budget
            callbacks.on_task_progress(
                task_id=task_id,
                progress=0.8,
                agent_id=self.agent_id,
                message="Validating budget",
            )
            
            optimized_total = Decimal(optimized.get("total_cost", "0"))
            
            # Store optimized plan in state (by correlation/task_id)
            await state_store.set(
                f"optimized_plan:{task_id}",
                optimized,
                ttl=3600,
            )
            # Also store by trace_id for convenience
            try:
                await state_store.set(
                    f"optimized_plan:{proposal_msg.trace_id}",
                    optimized,
                    ttl=3600,
                )
            except Exception:
                pass
            
            # Step 5: Send optimized plan via A2A
            a2a_adapter = get_a2a_adapter()
            optimized_msg = create_optimized_plan_message(
                plan_data=optimized,
                trace_id=proposal_msg.trace_id,
                correlation_id=proposal_msg.correlation_id,
                sender=self.agent_id,
                receiver="orchestrator",
            )
            
            await a2a_adapter.send_message(optimized_msg)
            
            callbacks.on_agent_message(
                task_id=task_id,
                agent_id=self.agent_id,
                message_type="optimized_plan",
                message=f"Sent optimized plan",
                data={"message_id": optimized_msg.message_id},
            )
            
            callbacks.on_task_end(
                task_id=task_id,
                agent_id=self.agent_id,
                message="ADK agent completed optimization",
                data={
                    "original_cost": str(estimated_total),
                    "optimized_cost": str(optimized_total),
                    "savings": str(estimated_total - optimized_total),
                },
            )
            
            return optimized
            
        except Exception as e:
            callbacks.on_task_error(
                task_id=task_id,
                error=e,
                agent_id=self.agent_id,
                message=f"Error in ADK optimization: {str(e)}",
            )
            raise
    
    async def _apply_optimization(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply LLM-based optimization algorithms to proposal.
        
        Args:
            proposal_data: Original proposal data
            
        Returns:
            Optimized data
        """
        logger.info("Applying AI-powered optimization")
        
        try:
            # Extract budget and currency
            budget_max = float(proposal_data.get("budget_max", 100000))
            currency = proposal_data.get("currency", "INR")
            
            # Convert Decimal values to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                return obj
            
            serializable_data = convert_decimals(proposal_data)
            
            # Build optimization prompt
            prompt = build_optimization_prompt(
                proposal_data={"itinerary": serializable_data},
                budget_max=budget_max,
                currency=currency,
            )
            
            # Call Groq LLM for optimization suggestions
            async with GroqClient() as groq:
                llm_response = await groq.chat(
                    prompt=prompt,
                    system_prompt="You are a budget optimization expert. Analyze travel itineraries and suggest cost-cutting measures while maintaining quality. Return JSON only with optimized itinerary and specific changes made.",
                    temperature=0.5,
                    max_tokens=2500,
                )
            
            # Parse LLM response
            try:
                json_str = llm_response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.startswith("```"):
                    json_str = json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                json_str = json_str.strip()
                
                optimized = json.loads(json_str)
                logger.info(f"Successfully applied LLM optimization: {optimized.get('cost_breakdown', {}).get('total', 'unknown')} total cost")
                
                # Ensure required fields are preserved from original
                if "optimization_applied" not in optimized:
                    optimized["optimization_applied"] = ["AI-powered optimization applied"]
                if "daily_schedule" not in optimized and "daily_schedule" in proposal_data:
                    optimized["daily_schedule"] = proposal_data["daily_schedule"]
                if "flights" not in optimized and "flights" in proposal_data:
                    optimized["flights"] = proposal_data["flights"]
                if "hotels" not in optimized and "hotels" in proposal_data:
                    optimized["hotels"] = proposal_data["hotels"]
                if "activities" not in optimized and "activities" in proposal_data:
                    optimized["activities"] = proposal_data["activities"]
                
                return optimized
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse optimization response: {e}")
                logger.error(f"LLM Response: {llm_response[:500]}")
                
                # Fallback: basic optimization
                return self._basic_optimization(proposal_data)
                
        except Exception as e:
            logger.error(f"Error in LLM optimization: {e}")
            return self._basic_optimization(proposal_data)
    
    def _basic_optimization(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback basic optimization if LLM fails."""
        # Keep structure but apply simple cost reduction
        optimized = proposal_data.copy()
        
        # Apply 10% discount as fallback
        try:
            original_total = float(proposal_data.get("estimated_total", 0))
            reduced_total = original_total * 0.9
            # Preserve and update cost_breakdown if present
            cb = optimized.get("cost_breakdown") or {}
            if cb:
                cb["total"] = reduced_total
                optimized["cost_breakdown"] = cb
            else:
                optimized["total_cost"] = reduced_total
            optimized["optimization_applied"] = [
                "Applied standard 10% cost optimization",
                "Selected best value options",
            ]
        except Exception:
            cb = optimized.get("cost_breakdown") or {}
            if cb and "total" in cb:
                optimized["cost_breakdown"] = cb
            else:
                optimized["total_cost"] = proposal_data.get("estimated_total", 0)
            optimized["optimization_applied"] = ["Standard optimization applied"]
        
        return optimized
    
    async def stop_listening(self) -> None:
        """Stop listening for A2A messages."""
        # TODO: Implement unsubscribe
        logger.info("ADK agent stopped listening")
