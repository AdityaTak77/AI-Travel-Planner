"""
MCP (Model Context Protocol) Client Wrapper.

This module provides a unified MCP client for integrating external tools
(Gemini, Groq, DuckDuckGo, Calculator) via the Model Context Protocol.

MCP enables standardized tool integration with:
- Server/client architecture for tool discovery
- Standardized request/response formats
- Resource and tool invocation management
- Streaming support for long-running operations
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class MCPToolDefinition(BaseModel):
    """MCP tool definition with schema."""
    
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    input_schema: Dict[str, Any] = Field(
        description="JSON Schema for tool input parameters"
    )
    category: str = Field(
        default="general",
        description="Tool category (research, generation, optimization, search, calculation)"
    )


class MCPToolRequest(BaseModel):
    """MCP tool invocation request."""
    
    tool_name: str = Field(description="Name of tool to invoke")
    arguments: Dict[str, Any] = Field(description="Tool arguments")
    trace_id: str = Field(description="Trace ID for request tracking")
    correlation_id: str = Field(description="Correlation ID for request tracking")


class MCPToolResponse(BaseModel):
    """MCP tool invocation response."""
    
    tool_name: str = Field(description="Tool that was invoked")
    result: Any = Field(description="Tool result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    trace_id: str = Field(description="Trace ID for request tracking")
    correlation_id: str = Field(description="Correlation ID for request tracking")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata"
    )


class MCPClient:
    """
    Unified MCP client for tool integration.
    
    This client manages tool discovery, invocation, and response handling
    following the Model Context Protocol standard.
    
    Supported tools:
    - Gemini Research (travel research)
    - Groq LLM (itinerary generation)
    - DuckDuckGo Search (web search)
    - Calculator (cost/budget calculations)
    """
    
    def __init__(self):
        """Initialize MCP client with tool registry."""
        self.tools_registry: Dict[str, MCPToolDefinition] = {}
        self._register_tools()
        logger.info(f"MCP client initialized with {len(self.tools_registry)} tools")
    
    def _register_tools(self) -> None:
        """Register all available MCP tools."""
        
        # Gemini Research Tool
        self.tools_registry["gemini_research"] = MCPToolDefinition(
            name="gemini_research",
            description="Research destination information using Gemini 2.0 Flash: weather, accommodations, attractions, tips, costs",
            category="research",
            input_schema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city/location to research"
                    },
                    "travel_dates": {
                        "type": "object",
                        "description": "Travel date range",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                        }
                    },
                    "interests": {
                        "type": "array",
                        "description": "Travel interests (e.g., culture, adventure, food)",
                        "items": {"type": "string"}
                    }
                },
                "required": ["destination"]
            }
        )
        
        # Groq LLM Tool
        self.tools_registry["groq_llm"] = MCPToolDefinition(
            name="groq_llm",
            description="Generate itinerary using Groq LLM with specified prompt and JSON mode",
            category="generation",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Input prompt for LLM"
                    },
                    "json_mode": {
                        "type": "boolean",
                        "description": "Enable JSON response mode",
                        "default": True
                    },
                    "temperature": {
                        "type": "number",
                        "description": "LLM temperature (0.0-2.0)",
                        "default": 0.7
                    }
                },
                "required": ["prompt"]
            }
        )
        
        # DuckDuckGo Search Tool
        self.tools_registry["duckduckgo_search"] = MCPToolDefinition(
            name="duckduckgo_search",
            description="Web search using DuckDuckGo for travel information",
            category="search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
        
        # Calculator Tool
        self.tools_registry["calculator"] = MCPToolDefinition(
            name="calculator",
            description="Calculate costs, budgets, and currency conversions",
            category="calculation",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation type (total_cost, per_day, convert_currency, budget_check)",
                        "enum": ["total_cost", "per_day", "convert_currency", "budget_check"]
                    },
                    "amounts": {
                        "type": "array",
                        "description": "Amounts to calculate",
                        "items": {"type": "number"}
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code"
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code"
                    },
                    "num_days": {
                        "type": "integer",
                        "description": "Number of days for per-day calculation"
                    }
                },
                "required": ["operation"]
            }
        )
        
        logger.debug(f"Registered {len(self.tools_registry)} MCP tools")
    
    def get_tool_definition(self, tool_name: str) -> Optional[MCPToolDefinition]:
        """Get MCP tool definition by name."""
        return self.tools_registry.get(tool_name)
    
    def list_tools(self) -> List[MCPToolDefinition]:
        """List all available MCP tools."""
        return list(self.tools_registry.values())
    
    async def invoke_tool(
        self,
        request: MCPToolRequest,
        tool_implementations: Dict[str, Any]
    ) -> MCPToolResponse:
        """
        Invoke an MCP tool with error handling and tracing.
        
        Args:
            request: Tool invocation request
            tool_implementations: Dict mapping tool_name -> implementation callable
        
        Returns:
            Tool response with result or error
        """
        tool_name = request.tool_name
        
        logger.info(
            f"MCP tool invocation",
            extra={
                "tool_name": tool_name,
                "trace_id": request.trace_id,
                "correlation_id": request.correlation_id,
                "arguments": str(request.arguments)[:100]  # truncate for logging
            }
        )
        
        try:
            # Validate tool exists
            if tool_name not in self.tools_registry:
                error_msg = f"Unknown MCP tool: {tool_name}"
                logger.error(error_msg)
                return MCPToolResponse(
                    tool_name=tool_name,
                    result=None,
                    error=error_msg,
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id
                )
            
            # Get tool implementation
            if tool_name not in tool_implementations:
                error_msg = f"No implementation for MCP tool: {tool_name}"
                logger.error(error_msg)
                return MCPToolResponse(
                    tool_name=tool_name,
                    result=None,
                    error=error_msg,
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id
                )
            
            # Invoke tool
            tool_fn = tool_implementations[tool_name]
            
            # Check if the result of calling tool_fn is a coroutine (for async methods)
            result = tool_fn(**request.arguments)
            
            # If it's a coroutine, await it
            if asyncio.iscoroutine(result):
                result = await result
            
            logger.info(
                f"MCP tool succeeded",
                extra={
                    "tool_name": tool_name,
                    "trace_id": request.trace_id,
                    "result_type": type(result).__name__
                }
            )
            
            return MCPToolResponse(
                tool_name=tool_name,
                result=result,
                trace_id=request.trace_id,
                correlation_id=request.correlation_id
            )
        
        except Exception as e:
            error_msg = f"MCP tool invocation failed: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "tool_name": tool_name,
                    "trace_id": request.trace_id,
                    "error": str(e)
                }
            )
            return MCPToolResponse(
                tool_name=tool_name,
                result=None,
                error=error_msg,
                trace_id=request.trace_id,
                correlation_id=request.correlation_id
            )


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
