# MCP (Model Context Protocol) Integration Guide

## Overview

This project implements the **Model Context Protocol (MCP)** for standardized, type-safe integration of external tools. MCP enables seamless discovery, validation, and invocation of tools with built-in observability and error handling.

## What is MCP?

The Model Context Protocol is a specification for tool integration that provides:

- **Tool Discovery**: Enumerate available tools and their schemas
- **Type Safety**: JSON Schema validation for tool inputs
- **Standardized Interface**: Consistent request/response envelopes
- **Observability**: Trace IDs and correlation IDs for distributed tracing
- **Error Handling**: Structured error responses

## Tools Integrated via MCP

### 1. Gemini Research Tool

**Name**: `gemini_research`  
**Category**: `research`  
**Purpose**: Travel destination research using Google Gemini 2.0 Flash

**Input Schema**:
```json
{
  "destination": "string (required)",
  "travel_dates": {
    "start_date": "string (YYYY-MM-DD)",
    "end_date": "string (YYYY-MM-DD)"
  },
  "interests": ["string array"]
}
```

**Output**:
```json
{
  "destination": "string",
  "weather_summary": "string",
  "accommodation_suggestions": "string",
  "top_attractions": "string",
  "estimated_daily_cost": "float",
  "currency": "string (e.g., USD)",
  "travel_tips": "string",
  "best_time_to_visit": "string"
}
```

**Example Usage**:
```python
from src.integrations.mcp_tool_adapter import invoke_mcp_tool
import uuid

response = await invoke_mcp_tool(
    tool_name="gemini_research",
    arguments={
        "destination": "Paris",
        "travel_dates": {
            "start_date": "2025-12-01",
            "end_date": "2025-12-07"
        },
        "interests": ["culture", "art", "food"]
    },
    trace_id=str(uuid.uuid4()),
    correlation_id=str(uuid.uuid4())
)

if not response.error:
    research = response.result
    print(f"Weather: {research['weather_summary']}")
    print(f"Daily cost: ${research['estimated_daily_cost']}")
```

### 2. Groq LLM Tool

**Name**: `groq_llm`  
**Category**: `generation`  
**Purpose**: Generate structured itineraries using Groq's fast inference

**Input Schema**:
```json
{
  "prompt": "string (required)",
  "json_mode": "boolean (default: true)",
  "temperature": "number (default: 0.7, range: 0.0-2.0)"
}
```

**Output**:
```json
{
  "response": "string or object (depending on json_mode)",
  "mode": "string (json|text)",
  "temperature": "number"
}
```

**Example Usage**:
```python
response = await invoke_mcp_tool(
    tool_name="groq_llm",
    arguments={
        "prompt": "Generate a 3-day Paris itinerary in JSON format...",
        "json_mode": True,
        "temperature": 0.7
    },
    trace_id=trace_id,
    correlation_id=correlation_id
)

if not response.error:
    itinerary = response.result["response"]
```

### 3. DuckDuckGo Search Tool

**Name**: `duckduckgo_search`  
**Category**: `search`  
**Purpose**: Web search for travel information and real-time data

**Input Schema**:
```json
{
  "query": "string (required)",
  "max_results": "integer (default: 10)"
}
```

**Output**:
```json
{
  "query": "string",
  "results": [
    {
      "title": "string",
      "url": "string",
      "snippet": "string"
    }
  ],
  "count": "integer"
}
```

**Example Usage**:
```python
response = await invoke_mcp_tool(
    tool_name="duckduckgo_search",
    arguments={
        "query": "Paris tourist attractions 2025",
        "max_results": 5
    },
    trace_id=trace_id,
    correlation_id=correlation_id
)

if not response.error:
    for result in response.result["results"]:
        print(f"- {result['title']}: {result['url']}")
```

### 4. Calculator Tool

**Name**: `calculator`  
**Category**: `calculation`  
**Purpose**: Budget calculations, cost optimization, and currency conversion

**Input Schema**:
```json
{
  "operation": "string (required, one of: total_cost, per_day, convert_currency, budget_check)",
  "amounts": "array of numbers",
  "from_currency": "string (currency code)",
  "to_currency": "string (currency code)",
  "num_days": "integer"
}
```

**Operations**:

- **total_cost**: Sum multiple amounts
  ```python
  response = await invoke_mcp_tool(
      tool_name="calculator",
      arguments={
          "operation": "total_cost",
          "amounts": [1500, 2000, 1200]
      },
      trace_id=trace_id,
      correlation_id=correlation_id
  )
  # Result: {"operation": "total_cost", "result": 4700}
  ```

- **per_day**: Calculate per-day average
  ```python
  response = await invoke_mcp_tool(
      tool_name="calculator",
      arguments={
          "operation": "per_day",
          "amounts": [5000],
          "num_days": 7
      },
      trace_id=trace_id,
      correlation_id=correlation_id
  )
  # Result: {"operation": "per_day", "total": 5000, "per_day": 714.29, "days": 7}
  ```

- **convert_currency**: Convert between currencies
  ```python
  response = await invoke_mcp_tool(
      tool_name="calculator",
      arguments={
          "operation": "convert_currency",
          "amounts": [1000],
          "from_currency": "USD",
          "to_currency": "EUR"
      },
      trace_id=trace_id,
      correlation_id=correlation_id
  )
  # Result: {"operation": "convert_currency", "amount": 1000, "from_currency": "USD", ...}
  ```

- **budget_check**: Validate spending against budget
  ```python
  response = await invoke_mcp_tool(
      tool_name="calculator",
      arguments={
          "operation": "budget_check",
          "amounts": [1500, 2000, 1200],
          "from_currency": "USD"
      },
      trace_id=trace_id,
      correlation_id=correlation_id
  )
  # Result: {"operation": "budget_check", "total_spent": 4700, "currency": "USD"}
  ```

## MCP Client API

### Discovery & Inspection

```python
from src.integrations.mcp_client import get_mcp_client

# Get MCP client instance
mcp = get_mcp_client()

# List all available tools
tools = mcp.list_tools()
print(f"Available tools: {len(tools)}")

# Get specific tool definition
tool = mcp.get_tool_definition("gemini_research")
print(f"Tool: {tool.name}")
print(f"Schema: {tool.input_schema}")
```

### Tool Invocation

```python
from src.integrations.mcp_tool_adapter import invoke_mcp_tool
import uuid

# Generate trace and correlation IDs
trace_id = str(uuid.uuid4())
correlation_id = str(uuid.uuid4())

# Invoke tool
response = await invoke_mcp_tool(
    tool_name="tool_name",
    arguments={...},
    trace_id=trace_id,
    correlation_id=correlation_id
)

# Check for errors
if response.error:
    print(f"Error: {response.error}")
else:
    result = response.result
```

### Response Structure

All MCP tool responses follow this structure:

```python
class MCPToolResponse:
    tool_name: str                          # Tool that was invoked
    result: Any                             # Tool result (None if error)
    error: Optional[str]                    # Error message if failed
    trace_id: str                           # Trace ID for request tracking
    correlation_id: str                     # Correlation ID for tracking
    metadata: Dict[str, Any]                # Response metadata
```

## Error Handling

MCP tools provide structured error responses:

```python
response = await invoke_mcp_tool(...)

if response.error:
    # Handle error gracefully
    logger.error(f"Tool failed: {response.error}", extra={
        "tool": response.tool_name,
        "trace_id": response.trace_id,
        "correlation_id": response.correlation_id
    })
    # Fallback logic here
else:
    # Process result
    result = response.result
```

## Distributed Tracing

MCP integrates with A2A protocol for distributed tracing:

```python
import uuid
from src.a2a.protocol import create_proposal_message

trace_id = str(uuid.uuid4())
correlation_id = str(uuid.uuid4())

# Invoke multiple tools within same request context
response1 = await invoke_mcp_tool(
    tool_name="gemini_research",
    arguments={...},
    trace_id=trace_id,
    correlation_id=correlation_id
)

response2 = await invoke_mcp_tool(
    tool_name="groq_llm",
    arguments={...},
    trace_id=trace_id,
    correlation_id=correlation_id
)

# All tools are linked by same trace_id and correlation_id
```

## Integration with Workflow

The interactive planner uses MCP tools automatically:

```python
from src.interactive_planner import search_destination_info

# Research via MCP Gemini tool
destination_info = await search_destination_info(
    destination="Paris",
    start_date=datetime(2025, 12, 1),
    end_date=datetime(2025, 12, 7),
    home_location="New York",
    budget_range=(3000, 5000),
    currency="USD"
)

# Returns research result via MCP
```

## Adding New MCP Tools

To add a new MCP tool:

1. **Create tool adapter** in `src/integrations/`:
```python
class MCPNewToolAdapter:
    async def invoke(self, argument1: str, argument2: int, **kwargs):
        # Implementation
        return result
```

2. **Register in MCP client** (`src/integrations/mcp_client.py`):
```python
def _register_tools(self):
    self.tools_registry["new_tool"] = MCPToolDefinition(
        name="new_tool",
        description="Tool description",
        category="category",
        input_schema={...}
    )
```

3. **Add adapter to registry** (`src/integrations/mcp_tool_adapter.py`):
```python
def get_tool_adapters():
    return {
        "new_tool": MCPNewToolAdapter().invoke,
        # ... other tools
    }
```

4. **Update documentation** with new tool details

## Testing MCP Integration

Run the demo script:
```bash
cd ai-travel-planner
python examples/mcp_demo.py
```

Expected output:
```
🚀 MCP Integration Test Suite
============================================================
MCP TOOL DISCOVERY
Found 4 MCP tools:
1. gemini_research
2. groq_llm
3. duckduckgo_search
4. calculator

✅ ALL MCP INTEGRATION TESTS PASSED!
```

## Configuration

MCP configuration is managed through environment variables:

- `GEMINI_API_KEY`: Gemini 2.0 Flash API key
- `GROQ_API_KEY`: Groq API key
- `A2A_SHARED_SECRET`: Shared secret for MCP message signing

## Performance Considerations

- **Tool Caching**: MCP client caches tool definitions (no overhead on repeated calls)
- **Error Fallbacks**: Tools implement graceful fallbacks for network/API errors
- **Async Support**: All tools are fully async-compatible for concurrent invocation
- **Rate Limiting**: Implement per-tool rate limiting if needed

## Compliance

✅ **MCP Requirement**: At least 2 external tools integrated
- Gemini 2.0 Flash (research)
- Groq LLM (generation)
- DuckDuckGo Search (search)
- Budget Calculator (calculation)

✅ **Tool Discovery**: `MCPClient.list_tools()` exposes all tools with schemas

✅ **Request/Response Format**: Standardized `MCPToolRequest` / `MCPToolResponse`

✅ **Error Handling**: All tools return structured errors with trace IDs

✅ **Async Support**: Full async compatibility for production workloads

---

**For more details, see the main README.md MCP Integration section.**
