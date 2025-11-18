"""
ResearchAgent: produces destination research via MCP tools and writes to state.

This agent aggregates structured research from the Gemini research tool and
web search results from DuckDuckGo, then stores the combined result in the
shared StateStore keyed by the task correlation_id for use by other agents.

Usage example:

    from datetime import datetime
    from src.models.itinerary import TaskContext, TravelerPreferences, TravelerProfile
    from src.agents.research_agent.agent import ResearchAgent

    ctx = TaskContext(
        task_id="task-1",
        correlation_id="corr-123",
        trace_id="trace-123",
        traveler_profile=TravelerProfile(
            traveler_id="u1",
            name="Alex",
            home_location="Jaipur, IN",
            preferences=TravelerPreferences(budget_min=1000, budget_max=3000)
        )
    )

    agent = ResearchAgent()
    result = await agent.run(
        context=ctx,
        destination="Jaipur",
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 5),
        interests=["heritage", "food"],
    )

The aggregated research is written to the StateStore under keys like:
    "{correlation_id}:research"
    "{correlation_id}:web_results"
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.integrations.mcp_tool_adapter import invoke_mcp_tool
from src.logging.json_logger import get_logger
from src.models.itinerary import TaskContext
from src.state.store import StateStore, get_state_store


logger = get_logger(__name__)


class ResearchAgent:
    """Agent that gathers destination research via MCP tools and persists it to state."""

    def __init__(self, agent_id: str = "research_agent", state_store: Optional[StateStore] = None) -> None:
        self.agent_id = agent_id
        self._state_store = state_store

    async def _store(self) -> StateStore:
        if self._state_store is None:
            self._state_store = await get_state_store()
        return self._state_store

    async def run(
        self,
        context: TaskContext,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        interests: Optional[List[str]] = None,
        max_results: int = 8,
        ttl_seconds: int = 1800,
    ) -> Dict[str, Any]:
        """
        Execute research workflow using MCP tools.

        - Calls "gemini_research" for structured destination insights
        - Calls "duckduckgo_search" for recent links
        - Writes aggregated results into StateStore with correlation_id

        Returns the aggregated research payload.
        """

        corr = context.correlation_id
        trace_id = context.trace_id or str(uuid.uuid4())

        logger.info(
            "ResearchAgent started",
            extra={
                "agent_id": self.agent_id,
                "destination": destination,
                "correlation_id": corr,
                "trace_id": trace_id,
            },
        )

        # Invoke Gemini research via MCP
        gemini_args: Dict[str, Any] = {
            "destination": destination,
            "travel_dates": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
            "interests": interests or [],
        }
        gemini_resp = await invoke_mcp_tool(
            tool_name="gemini_research",
            arguments=gemini_args,
            trace_id=trace_id,
            correlation_id=corr,
        )

        if gemini_resp.error:
            logger.error(
                "Gemini research failed",
                extra={"agent_id": self.agent_id, "error": gemini_resp.error, "correlation_id": corr},
            )
            raise RuntimeError(f"Gemini research error: {gemini_resp.error}")

        gemini_data = gemini_resp.result or {}

        # Invoke DuckDuckGo search via MCP for supplementary links
        ddg_query = f"{destination} travel tips and best places to visit"
        ddg_resp = await invoke_mcp_tool(
            tool_name="duckduckgo_search",
            arguments={"query": ddg_query, "max_results": max_results},
            trace_id=trace_id,
            correlation_id=corr,
        )

        if ddg_resp.error:
            logger.error(
                "DuckDuckGo search failed",
                extra={"agent_id": self.agent_id, "error": ddg_resp.error, "correlation_id": corr},
            )
            raise RuntimeError(f"DuckDuckGo search error: {ddg_resp.error}")

        web_results = (ddg_resp.result or {}).get("results", [])

        aggregated: Dict[str, Any] = {
            "destination": destination,
            "date_range": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
            "interests": interests or [],
            # Fields returned by MCPGeminiAdapter
            "weather_summary": gemini_data.get("weather_summary"),
            "accommodation_suggestions": gemini_data.get("accommodation_suggestions", []),
            "top_attractions": gemini_data.get("top_attractions", []),
            "estimated_daily_cost": gemini_data.get("estimated_daily_cost"),
            "currency": gemini_data.get("currency"),
            "travel_tips": gemini_data.get("travel_tips", []),
            "best_time_to_visit": gemini_data.get("best_time_to_visit"),
            # Supplementary links
            "web_results": web_results,
            "source_tools": ["gemini_research", "duckduckgo_search"],
        }

        store = await self._store()
        await store.set(f"{corr}:research", aggregated, ttl=ttl_seconds)
        await store.set(f"{corr}:web_results", web_results, ttl=ttl_seconds)

        logger.info(
            "ResearchAgent completed",
            extra={
                "agent_id": self.agent_id,
                "correlation_id": corr,
                "trace_id": trace_id,
                "stored_keys": [f"{corr}:research", f"{corr}:web_results"],
            },
        )

        return aggregated
