"""
Gemini-based travel research client.

Uses Google's Gemini 2.0 Flash model to research destinations,
weather, accommodations, and attractions with real-time information.
"""

import json
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


class ResearchResult(BaseModel):
    """Travel research result."""
    
    destination: str = Field(description="Destination being researched")
    weather_summary: str = Field(description="Weather information and conditions")
    accommodation_suggestions: str = Field(description="Hotel and stay recommendations")
    top_attractions: str = Field(description="Must-see attractions and activities")
    estimated_daily_cost: float = Field(description="Estimated daily cost in local currency")
    currency: str = Field(description="Local currency code")
    travel_tips: str = Field(description="Important travel tips and advice")
    best_time_to_visit: str = Field(description="Best time/season to visit")


class GeminiResearchClient:
    """
    Client for travel research using Gemini 2.0 Flash.
    
    Uses Gemini's grounding and real-time capabilities to fetch
    current travel information, weather forecasts, and recommendations.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Gemini research client."""
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        
        if not self.api_key or self.api_key == "placeholder-gemini-key":
            logger.warning("Gemini API key not configured - research will use mock data")
            self.api_key = None
        
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def research_destination(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        home_location: str,
        budget_range: tuple[float, float],
        currency: str = "INR",
    ) -> ResearchResult:
        """
        Research a travel destination comprehensively.
        
        Args:
            destination: Destination city/location
            start_date: Trip start date (YYYY-MM-DD)
            end_date: Trip end date (YYYY-MM-DD)
            home_location: Traveler's home city
            budget_range: (min, max) budget tuple
            currency: Currency code
            
        Returns:
            Comprehensive research results
        """
        logger.info(f"Researching {destination} using Gemini {self.model}")
        
        if not self.api_key:
            return await self._mock_research(destination, currency)
        
        try:
            prompt = f"""You are a travel research assistant. Provide comprehensive, accurate, and up-to-date information about traveling to {destination}.

Trip Details:
- Destination: {destination}
- Travel Dates: {start_date} to {end_date}
- Home Location: {home_location}
- Budget Range: {currency} {budget_range[0]:,.0f} to {budget_range[1]:,.0f}

Please research and provide the following information in JSON format:

1. **weather_summary**: Current weather conditions and forecast for the travel dates. Include temperature ranges, rainfall, and what to pack.

2. **accommodation_suggestions**: Recommend 3-5 hotels or stays with different price ranges (budget, mid-range, luxury). Include names, approximate costs, and why they're recommended.

3. **top_attractions**: List 8-10 must-visit places, activities, and experiences. Include both popular and hidden gems. Mention approximate costs and duration.

4. **estimated_daily_cost**: Calculate realistic daily expenses including food, local transport, and activities (in {currency}).

5. **travel_tips**: Important tips including:
   - Best way to travel from {home_location} to {destination}
   - Local transportation options
   - Safety considerations
   - Cultural etiquette
   - Must-try local food
   - Things to avoid

6. **best_time_to_visit**: Is the travel period ({{start_date}} to {end_date}) a good time? Any festivals, events, or weather considerations?

Respond ONLY with valid JSON in this exact format:
{{
    "destination": "{destination}",
    "weather_summary": "detailed weather info...",
    "accommodation_suggestions": "hotel recommendations...",
    "top_attractions": "places to visit...",
    "estimated_daily_cost": 5000,
    "currency": "{currency}",
    "travel_tips": "important tips...",
    "best_time_to_visit": "timing analysis..."
}}"""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = await self._client.post(
                url,
                params={"key": self.api_key},
                json=payload,
                headers=headers,
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract text from Gemini response
            if "candidates" in result and len(result["candidates"]) > 0:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Try to parse JSON from the response
                # Gemini might wrap it in markdown code blocks
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                research_data = json.loads(text)
                
                # Convert nested objects to formatted strings
                def format_value(value):
                    if isinstance(value, dict):
                        return json.dumps(value, indent=2, ensure_ascii=False)
                    return str(value)
                
                formatted_data = {
                    "destination": research_data.get("destination", destination),
                    "weather_summary": format_value(research_data.get("weather_summary", "")),
                    "accommodation_suggestions": format_value(research_data.get("accommodation_suggestions", "")),
                    "top_attractions": format_value(research_data.get("top_attractions", "")),
                    "estimated_daily_cost": float(research_data.get("estimated_daily_cost", 5000)),
                    "currency": research_data.get("currency", currency),
                    "travel_tips": format_value(research_data.get("travel_tips", "")),
                    "best_time_to_visit": format_value(research_data.get("best_time_to_visit", "")),
                }
                
                logger.info(f"Successfully researched {destination}")
                return ResearchResult(**formatted_data)
            else:
                logger.error("No candidates in Gemini response")
                return await self._mock_research(destination, currency)
                
        except Exception as e:
            logger.error(f"Gemini research error: {e}", exc_info=True)
            return await self._mock_research(destination, currency)
    
    async def _mock_research(self, destination: str, currency: str) -> ResearchResult:
        """Return mock research data when API is unavailable."""
        logger.warning(f"Using mock research data for {destination}")
        
        return ResearchResult(
            destination=destination,
            weather_summary=f"The weather in {destination} during your travel dates is generally pleasant. Temperatures range from 15-28°C. Pack light cotton clothes, sunscreen, and a light jacket for evenings. Minimal rainfall expected.",
            accommodation_suggestions=f"""Recommended stays in {destination}:
            
1. **Luxury**: The Royal Palace Hotel - {currency} 8,000-15,000/night. Premium amenities, spa, rooftop restaurant.
2. **Mid-Range**: Heritage Haveli - {currency} 3,000-6,000/night. Traditional architecture, central location.
3. **Budget**: Backpacker's Inn - {currency} 800-1,500/night. Clean, social atmosphere, near attractions.
4. **Boutique**: Artist's Retreat - {currency} 4,500-7,000/night. Unique rooms, art gallery, cafe.
5. **Homestay**: Local Family Stay - {currency} 1,200-2,500/night. Authentic experience, home-cooked meals.""",
            top_attractions=f"""Must-visit places in {destination}:
            
1. **Historic Fort/Palace** - 2-3 hours, {currency} 500 entry
2. **Local Markets & Bazaars** - Half day, free browsing
3. **Temple/Religious Site** - 1-2 hours, {currency} 200 entry
4. **Sunset Point/Viewpoint** - Evening visit, free
5. **Museum/Art Gallery** - 2 hours, {currency} 300 entry
6. **Traditional Food Street** - Evening, {currency} 800-1200 per person
7. **Gardens/Parks** - Morning visit, {currency} 50 entry
8. **Cultural Show/Performance** - Evening, {currency} 600-1000 per ticket
9. **Local Craft Village** - Half day, free entry
10. **Adventure Activity** - Full day, {currency} 2000-3000""",
            estimated_daily_cost=4500.0,
            currency=currency,
            travel_tips=f"""Important tips for {destination}:
            
**Getting There**: Multiple flight options available. Consider booking trains for a scenic journey.

**Local Transport**: Auto-rickshaws (₹30-100), app-based cabs (affordable), local buses (₹10-30).

**Safety**: Generally safe for tourists. Keep valuables secure, avoid isolated areas at night.

**Culture**: Modest dress at religious sites. Remove shoes before entering temples. Ask before photographing people.

**Food**: Try local specialties. Street food is generally safe from popular vendors. Stay hydrated.

**Bargaining**: Expected in markets. Start at 40-50% of quoted price.

**Avoid**: Overly friendly strangers offering tours, taxi touts at tourist spots, unauthorized guides.""",
            best_time_to_visit=f"Your travel dates are excellent for visiting {destination}. The weather is pleasant, perfect for sightseeing. This period avoids peak summer heat and monsoon rains. Popular with tourists but not overcrowded. Check for any local festivals during your dates - they offer authentic cultural experiences!",
        )
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
