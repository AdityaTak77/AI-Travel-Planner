"""
MCP Tool Integration Adapter.

This module provides adapters that integrate existing tools (Gemini, Groq, DuckDuckGo, Calculator)
with the MCP protocol, enabling standardized tool invocation and response handling.
"""

import json
from typing import Any, Dict, Optional

from src.integrations.gemini_research import GeminiResearchClient
from src.integrations.groq_client import GroqClient
from src.integrations.duckduckgo_client import DuckDuckGoClient
from src.integrations.calculator import BudgetCalculator
from src.integrations.mcp_client import MCPToolRequest, MCPToolResponse, get_mcp_client
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class MCPGeminiAdapter:
    """MCP adapter for Gemini research tool."""
    
    def __init__(self, client: Optional[GeminiResearchClient] = None):
        """Initialize adapter."""
        self.client = client or GeminiResearchClient()
    
    async def research(
        self,
        destination: str,
        travel_dates: Optional[Dict[str, str]] = None,
        interests: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP-compliant research tool.
        
        Args:
            destination: Destination to research
            travel_dates: Travel date range
            interests: Travel interests
            
        Returns:
            Research result dict
        """
        logger.info(
            f"MCP Gemini research initiated",
            extra={"destination": destination, "interests": interests}
        )
        
        # Call the async research method and await it
        result = await self.client.research_destination(
            destination=destination,
            start_date=travel_dates.get("start_date") if travel_dates else None,
            end_date=travel_dates.get("end_date") if travel_dates else None,
            home_location=destination,
            budget_range=(0, 999999),
            currency="INR"
        )
        
        return {
            "destination": destination,
            "weather_summary": result.weather_summary,
            "accommodation_suggestions": result.accommodation_suggestions,
            "top_attractions": result.top_attractions,
            "estimated_daily_cost": result.estimated_daily_cost,
            "currency": result.currency,
            "travel_tips": result.travel_tips,
            "best_time_to_visit": result.best_time_to_visit
        }


class MCPGroqAdapter:
    """MCP adapter for Groq LLM tool."""
    
    def __init__(self, client: Optional[GroqClient] = None):
        """Initialize adapter."""
        self.client = client or GroqClient()
    
    async def generate(
        self,
        prompt: str,
        json_mode: bool = True,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP-compliant LLM generation tool.
        
        Args:
            prompt: Input prompt
            json_mode: Enable JSON response mode
            temperature: LLM temperature
            
        Returns:
            LLM response dict
        """
        logger.info(
            f"MCP Groq LLM invoked",
            extra={"json_mode": json_mode, "temperature": temperature}
        )
        
        if json_mode:
            result = await self.client.chat(prompt, json_mode=True)
        else:
            result = await self.client.chat(prompt)
        
        return {
            "response": result,
            "mode": "json" if json_mode else "text",
            "temperature": temperature
        }


class MCPDuckDuckGoAdapter:
    """MCP adapter for DuckDuckGo search tool."""
    
    def __init__(self, client: Optional[DuckDuckGoClient] = None):
        """Initialize adapter."""
        self.client = client or DuckDuckGoClient()
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP-compliant web search tool.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            Search results dict
        """
        logger.info(
            f"MCP DuckDuckGo search initiated",
            extra={"query": query, "max_results": max_results}
        )
        
        results = await self.client.search(query, max_results=max_results)
        
        return {
            "query": query,
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", "")
                }
                for r in results
            ],
            "count": len(results)
        }


class MCPCalculatorAdapter:
    """MCP adapter for calculator tool."""
    
    def __init__(self, calculator: Optional[BudgetCalculator] = None):
        """Initialize adapter."""
        self.calculator = calculator or BudgetCalculator()
    
    async def calculate(
        self,
        operation: str,
        amounts: Optional[list] = None,
        from_currency: Optional[str] = None,
        to_currency: Optional[str] = None,
        num_days: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP-compliant calculator tool.
        
        Args:
            operation: Operation type (total_cost, per_day, convert_currency, budget_check)
            amounts: Amounts to calculate
            from_currency: Source currency
            to_currency: Target currency
            num_days: Number of days for per-day calculation
            
        Returns:
            Calculation result dict
        """
        logger.info(
            f"MCP Calculator invoked",
            extra={"operation": operation, "num_days": num_days}
        )
        
        if operation == "total_cost" and amounts:
            result = sum(amounts)
            return {"operation": operation, "result": result}
        
        elif operation == "per_day" and amounts and num_days:
            total = sum(amounts)
            per_day = total / num_days if num_days > 0 else 0
            return {"operation": operation, "total": total, "per_day": per_day, "days": num_days}
        
        elif operation == "convert_currency" and amounts and from_currency and to_currency:
            # Placeholder conversion (would use real rates)
            converted = amounts[0] * 1.0  # Same rate for demo
            return {
                "operation": operation,
                "amount": amounts[0],
                "from_currency": from_currency,
                "to_currency": to_currency,
                "converted_amount": converted
            }
        
        elif operation == "budget_check" and amounts and from_currency:
            total = sum(amounts)
            return {
                "operation": operation,
                "total_spent": total,
                "currency": from_currency
            }
        
        else:
            raise ValueError(f"Invalid calculator operation: {operation}")


# Global tool adapters registry
_tool_adapters: Dict[str, Any] = {}


def get_tool_adapters() -> Dict[str, Any]:
    """Get or initialize tool adapters."""
    global _tool_adapters
    if not _tool_adapters:
        _tool_adapters = {
            "gemini_research": MCPGeminiAdapter().research,
            "groq_llm": MCPGroqAdapter().generate,
            "duckduckgo_search": MCPDuckDuckGoAdapter().search,
            "calculator": MCPCalculatorAdapter().calculate
        }
        logger.info("MCP tool adapters initialized", extra={"count": len(_tool_adapters)})
    return _tool_adapters


async def invoke_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    trace_id: str,
    correlation_id: str
) -> MCPToolResponse:
    """
    Invoke an MCP tool through the standard interface.
    
    Args:
        tool_name: Name of tool to invoke
        arguments: Tool arguments
        trace_id: Trace ID for tracking
        correlation_id: Correlation ID for tracking
        
    Returns:
        Tool response
    """
    mcp_client = get_mcp_client()
    
    request = MCPToolRequest(
        tool_name=tool_name,
        arguments=arguments,
        trace_id=trace_id,
        correlation_id=correlation_id
    )
    
    tool_adapters = get_tool_adapters()
    return await mcp_client.invoke_tool(request, tool_adapters)
