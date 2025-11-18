"""
Intelligent planning prompts and LLM integration helpers.
"""

import json
from datetime import datetime
from typing import Any, Dict
from datetime import datetime
from decimal import Decimal

from src.models.itinerary import TravelerProfile


def build_planning_prompt(
    profile: TravelerProfile,
    request_params: Dict[str, Any],
    research_data: Dict[str, Any],
) -> str:
    """
    Build a comprehensive prompt for LLM-based itinerary planning.
    
    Args:
        profile: Traveler profile with preferences
        request_params: Trip parameters (destination, dates, etc.)
        research_data: Gemini research results
        
    Returns:
        Formatted prompt string
    """
    destination = request_params.get("destination", "destination")
    start_date = request_params.get("start_date", "")
    end_date = request_params.get("end_date", "")
    currency = request_params.get("currency", "INR")
    
    # Parse dates if they're strings
    if isinstance(start_date, str):
        start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        start_date_str = start_date_obj.strftime("%B %d, %Y")
    else:
        start_date_str = start_date.strftime("%B %d, %Y") if hasattr(start_date, 'strftime') else str(start_date)
    
    if isinstance(end_date, str):
        end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        end_date_str = end_date_obj.strftime("%B %d, %Y")
        num_days = (end_date_obj - start_date_obj).days
    else:
        end_date_str = end_date.strftime("%B %d, %Y") if hasattr(end_date, 'strftime') else str(end_date)
        num_days = 7
    
    # Extract research insights
    weather_info = research_data.get("weather", "")
    accommodations = research_data.get("accommodation", "")
    attractions = research_data.get("attractions", "")
    daily_cost = research_data.get("estimated_daily_cost", 5000)
    travel_tips = research_data.get("travel_tips", "")
    
    prompt = f"""Create a detailed {num_days}-day travel itinerary for the following trip:

**TRAVELER PROFILE:**
- Name: {profile.name}
- Home Location: {profile.home_location}
- Budget: {currency} {float(profile.preferences.budget_min):,.0f} - {float(profile.preferences.budget_max):,.0f}
- Travel Style: {profile.preferences.travel_style}
- Interests: {', '.join(profile.preferences.interests)}
- Dietary Restrictions: {', '.join(profile.preferences.dietary_restrictions) if profile.preferences.dietary_restrictions else 'None'}

**TRIP DETAILS:**
- Destination: {destination}
- Start Date: {start_date_str}
- End Date: {end_date_str}
- Duration: {num_days} days

**RESEARCH DATA:**

Weather Information:
{weather_info[:500]}

Recommended Accommodations:
{accommodations[:500]}

Top Attractions:
{attractions[:800]}

Estimated Daily Cost: {currency} {daily_cost}

Travel Tips:
{travel_tips[:500]}

**TASK:**
Create a comprehensive day-by-day itinerary with:

1. **Daily Schedule**: For each day, include 3-5 activities/attractions with:
   - Time slots (e.g., 9:00 AM - 11:00 AM)
   - Activity name and description
   - Location details
   - Estimated cost in {currency}
   - Duration
   - Transportation method

2. **Accommodation**: Recommend a specific hotel/stay with:
   - Name
   - Approximate cost per night in {currency}
   - Why it's suitable for this traveler

3. **Meals**: Suggest 2-3 restaurants per day with cuisine type and budget

4. **Transportation**: Include how to get from {profile.home_location} to {destination} and local transport

5. **Total Cost Breakdown**:
   - Accommodation total
   - Activities/attractions total
   - Food total
   - Transportation total
   - Buffer for miscellaneous
   - **Grand Total** (must be within budget: {currency} {float(profile.preferences.budget_min):,.0f} - {float(profile.preferences.budget_max):,.0f})

6. **Important Notes**: Any tips, warnings, or special considerations

Return ONLY valid JSON in this exact structure:
{{
  "destination": "{destination}",
  "duration_days": {num_days},
  "accommodation": {{
    "name": "Hotel Name",
    "cost_per_night": 3500,
    "total_nights": {num_days - 1},
    "total_cost": 31500,
    "recommendation": "Why this hotel..."
  }},
  "daily_schedule": [
    {{
      "day": 1,
      "date": "{start_date_str}",
      "activities": [
        {{
          "time": "9:00 AM - 11:00 AM",
          "name": "Activity Name",
          "description": "What you'll do...",
          "location": "Specific location",
          "cost": 500,
          "transportation": "Auto-rickshaw"
        }}
      ],
      "meals": [
        {{
          "time": "lunch",
          "restaurant": "Restaurant Name",
          "cuisine": "Rajasthani",
          "estimated_cost": 800
        }}
      ],
      "total_day_cost": 3500
    }}
  ],
  "transportation": {{
    "to_destination": {{
      "method": "Train/Flight/Bus",
      "cost": 2500,
      "duration": "3 hours"
    }},
    "local": "Auto-rickshaw, taxi apps",
    "estimated_local_cost": 2000
  }},
  "cost_breakdown": {{
    "accommodation": 31500,
    "activities": 8000,
    "food": 12000,
    "transportation": 5000,
    "miscellaneous": 3500,
    "total": 60000,
    "currency": "{currency}"
  }},
  "special_notes": "Important tips and reminders..."
}}

CRITICAL: Return ONLY the JSON, no markdown formatting, no explanations."""
    
    return prompt


def build_optimization_prompt(
  proposal_data: Dict[str, Any],
  budget_max: float,
  currency: str,
) -> str:
    """
    Build prompt for itinerary optimization.
    
    Args:
        proposal_data: Initial itinerary proposal
        budget_max: Maximum budget
        currency: Currency code
        
    Returns:
        Optimization prompt
    """
    current_total = proposal_data.get("itinerary", {}).get("cost_breakdown", {}).get("total", 0)

    def _json_default(o: Any):
      if isinstance(o, Decimal):
        return float(o)
      if isinstance(o, datetime):
        return o.isoformat()
      return str(o)
    
    prompt = f"""You are a budget optimization expert. Analyze this travel itinerary and optimize it to reduce costs while maintaining quality.

**CURRENT ITINERARY:**
{json.dumps(proposal_data.get("itinerary", {}), indent=2, default=_json_default)}

**CONSTRAINTS:**
- Maximum Budget: {currency} {budget_max:,.0f}
- Current Total: {currency} {current_total:,.0f}
- Budget Status: {"OVER BUDGET" if current_total > budget_max else "Within budget"}

**OPTIMIZATION TASKS:**
1. If over budget, suggest cost-cutting measures:
   - Cheaper accommodation alternatives (but still good quality)
   - Free or low-cost activities
   - Budget-friendly restaurants
   - Public transport instead of taxis

2. Improve efficiency:
   - Group nearby attractions on same days
   - Optimize travel routes
   - Suggest time-saving tips

3. Add value:
   - Free attractions or viewpoints
   - Local experiences
   - Money-saving tips

Return the OPTIMIZED itinerary in the SAME JSON structure, with:
- Updated costs
- Better activity ordering
- Cost-saving suggestions in "optimization_notes" field
- New "cost_breakdown" with reduced total

Return ONLY valid JSON, no explanations."""
    
    return prompt
