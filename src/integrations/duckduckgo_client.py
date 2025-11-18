"""
DuckDuckGo search client wrapper.

Provides a thin client for DuckDuckGo search API.
Used for web search and real-time information retrieval.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel, Field

from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """A single search result."""
    
    title: str = Field(description="Result title")
    url: str = Field(description="Result URL")
    snippet: str = Field(description="Result snippet/description")
    source: Optional[str] = Field(default=None, description="Source domain")


class DuckDuckGoSearchResponse(BaseModel):
    """Response from DuckDuckGo search."""
    
    query: str = Field(description="Original search query")
    results: List[SearchResult] = Field(description="Search results")
    total_results: int = Field(description="Total number of results")


class DuckDuckGoClient:
    """
    Client for DuckDuckGo search.
    
    NOTE: This uses DuckDuckGo's HTML interface as they don't have an official API.
    In production, consider using:
    1. duckduckgo-search Python package
    2. Alternative search APIs (Bing, Google Custom Search)
    3. Web scraping with proper user-agent and rate limiting
    """
    
    def __init__(self) -> None:
        """Initialize DuckDuckGo client."""
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AI-Travel-Planner/1.0)",
            },
            follow_redirects=True,
        )
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        region: str = "wt-wt",
    ) -> DuckDuckGoSearchResponse:
        """
        Perform a web search.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            region: Region code (default: worldwide)
            
        Returns:
            Search response with results
        """
        logger.info(f"DuckDuckGo search: {query}", extra={"query": query})
        
        try:
            # Try to use duckduckgo-search package
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                
                results = [
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source=r.get("hostname"),
                    )
                    for r in raw_results
                ]
                
                logger.info(f"Found {len(results)} results for: {query}")
                
                return DuckDuckGoSearchResponse(
                    query=query,
                    results=results,
                    total_results=len(results),
                )
                
        except ImportError:
            logger.warning("duckduckgo-search not installed - returning mock results")
            logger.warning("Install with: pip install duckduckgo-search")
            
            # Fallback to stub implementation
            mock_results = [
                SearchResult(
                    title=f"Result {i+1} for {query}",
                    url=f"https://example.com/result-{i+1}",
                    snippet=f"This is a mock search result for the query: {query}",
                    source="example.com",
                )
                for i in range(min(3, max_results))
            ]
            
            return DuckDuckGoSearchResponse(
                query=query,
                results=mock_results,
                total_results=len(mock_results),
            )
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            # Return empty results on error
            return DuckDuckGoSearchResponse(
                query=query,
                results=[],
                total_results=0,
            )
    
    async def search_travel(
        self,
        destination: str,
        query_type: str = "attractions",
    ) -> DuckDuckGoSearchResponse:
        """
        Search for travel-related information.
        
        Args:
            destination: Destination name
            query_type: Type of query (attractions, hotels, restaurants, activities)
            
        Returns:
            Search response
        """
        query = f"{destination} {query_type}"
        return await self.search(query)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self) -> "DuckDuckGoClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Note: For production use, consider installing and using the duckduckgo-search package:
# pip install duckduckgo-search
# Then replace the stub implementation above with:
#
# from duckduckgo_search import DDGS
#
# async def search(self, query: str, max_results: int = 10):
#     with DDGS() as ddgs:
#         results = list(ddgs.text(query, max_results=max_results))
#         return DuckDuckGoSearchResponse(
#             query=query,
#             results=[
#                 SearchResult(
#                     title=r["title"],
#                     url=r["href"],
#                     snippet=r["body"],
#                     source=r.get("hostname"),
#                 )
#                 for r in results
#             ],
#             total_results=len(results),
#         )
