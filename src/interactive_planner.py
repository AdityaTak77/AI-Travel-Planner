"""
Interactive AI Travel Planner CLI.

This script provides an interactive command-line interface for creating
personalized travel itineraries with real-time weather and location research.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from src.agents.adk_agent.agent import ADKAgent
from src.agents.crewai_agent.agent import CrewAIAgent
from src.callbacks.logger_adapter import create_monitoring_listener
from src.config.settings import get_settings
from src.integrations.gemini_research import GeminiResearchClient
from src.integrations.mcp_tool_adapter import invoke_mcp_tool, get_tool_adapters
from src.integrations.mcp_client import get_mcp_client
import uuid
from src.logging.json_logger import get_logger
from src.models.itinerary import TaskContext, TravelerPreferences, TravelerProfile
from src.workflows.dynamic_planner import DynamicPlannerWorkflow

logger = get_logger(__name__)


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 80)
    print("🌍 AI TRAVEL PLANNER - Interactive Mode 🌍".center(80))
    print("=" * 80 + "\n")


def get_user_input(prompt: str, default: Optional[str] = None) -> str:
    """Get input from user with optional default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else (default or "")


def get_date_input(prompt: str) -> datetime:
    """Get date input from user."""
    while True:
        date_str = get_user_input(prompt, "YYYY-MM-DD")
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2025-12-15)")


def get_number_input(prompt: str, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """Get numeric input from user."""
    while True:
        try:
            value = float(get_user_input(prompt))
            if min_val is not None and value < min_val:
                print(f"❌ Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"❌ Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("❌ Please enter a valid number")


async def search_destination_info(destination: str, start_date: datetime, end_date: datetime, home_location: str, budget_range: tuple, currency: str) -> dict:
    """Search for destination weather and travel information using Gemini via MCP."""
    print(f"\n🔍 Researching {destination} with Gemini 2.0 Flash (via MCP)...")
    
    # Generate trace and correlation IDs for MCP tracking
    trace_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    
    try:
        # Invoke Gemini research tool via MCP protocol
        response = await invoke_mcp_tool(
            tool_name="gemini_research",
            arguments={
                "destination": destination,
                "travel_dates": {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                },
                "interests": ["travel", "culture"]
            },
            trace_id=trace_id,
            correlation_id=correlation_id
        )
        
        if response.error:
            print(f"   ⚠️ MCP research encountered an issue: {response.error}")
            print(f"   Falling back to direct Gemini client...")
            # Fallback to direct client
            gemini = GeminiResearchClient()
            research = await gemini.research_destination(
                destination=destination,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                home_location=home_location,
                budget_range=budget_range,
                currency=currency,
            )
        else:
            # response.result is already the dict from MCPGeminiAdapter
            research = response.result
        
        print(f"   ✅ Research completed successfully!\n")
        
        # Extract research data (MCP response or fallback)
        if isinstance(research, dict):
            return {
                "weather": research.get("weather_summary", ""),
                "accommodation": research.get("accommodation_suggestions", ""),
                "attractions": research.get("top_attractions", ""),
                "estimated_daily_cost": research.get("estimated_daily_cost", 0),
                "travel_tips": research.get("travel_tips", ""),
                "best_time": research.get("best_time_to_visit", ""),
            }
        else:
            # If Pydantic model (from fallback)
            return {
                "weather": research.weather_summary,
                "accommodation": research.accommodation_suggestions,
                "attractions": research.top_attractions,
                "estimated_daily_cost": research.estimated_daily_cost,
                "travel_tips": research.travel_tips,
                "best_time": research.best_time_to_visit,
            }
        
    except Exception as e:
        print(f"   ⚠️ Research failed: {e}")
        # Return empty research data to continue workflow
        return {
            "weather": "Unable to fetch weather data",
            "accommodation": "Unable to fetch accommodation data",
            "attractions": "Unable to fetch attractions data",
            "estimated_daily_cost": 0,
            "travel_tips": "Unable to fetch travel tips",
            "best_time": "Unable to fetch best time info",
        }


def display_search_results(info: dict):
    """Display search results to user."""
    print("\n" + "=" * 80)
    print("📊 RESEARCH RESULTS".center(80))
    print("=" * 80 + "\n")
    
    if info.get("weather"):
        print("🌤️  WEATHER INFORMATION:")
        print(f"   {info['weather']}\n")
    
    if info.get("accommodation"):
        print("🏨 ACCOMMODATION SUGGESTIONS:")
        print(f"   {info['accommodation']}\n")
    
    if info.get("attractions"):
        print("🎭 TOP ATTRACTIONS:")
        print(f"   {info['attractions']}\n")
    
    if info.get("estimated_daily_cost"):
        print(f"💰 ESTIMATED DAILY COST: {info['estimated_daily_cost']:.0f}\n")
    
    if info.get("travel_tips"):
        print("💡 TRAVEL TIPS:")
        print(f"   {info['travel_tips']}\n")
    
    if info.get("best_time"):
        print("📅 TIMING ANALYSIS:")
        print(f"   {info['best_time']}\n")
    
    print("=" * 80 + "\n")


async def interactive_planning():
    """Run interactive travel planning session."""
    settings = get_settings()
    print_banner()
    
    print("Let's plan your perfect trip! 🎉\n")
    
    # Collect traveler information
    print("👤 TRAVELER INFORMATION")
    print("-" * 40)
    name = get_user_input("Your name", "Traveler")
    email = get_user_input("Your email (optional)")
    home_location = get_user_input("Your home city", "Mumbai")
    
    # Collect trip details
    print("\n✈️  TRIP DETAILS")
    print("-" * 40)
    destination = get_user_input("Where do you want to go?", "Goa")
    
    print("\n📅 Travel Dates")
    start_date = get_date_input("Start date")
    end_date = get_date_input("End date")
    
    # Budget information
    print("\n💰 BUDGET")
    print("-" * 40)
    currency = get_user_input("Currency", "INR")
    budget_min = get_number_input(f"Minimum budget ({currency})", min_val=0)
    budget_max = get_number_input(f"Maximum budget ({currency})", min_val=budget_min)
    
    # Preferences
    print("\n🎯 PREFERENCES")
    print("-" * 40)
    travel_style = get_user_input("Travel style (luxury/balanced/budget)", "balanced")
    interests_input = get_user_input("Interests (comma-separated)", "culture, food, beaches")
    interests = [i.strip() for i in interests_input.split(",")]
    
    dietary_input = get_user_input("Dietary restrictions (comma-separated, or press Enter to skip)")
    dietary_restrictions = [d.strip() for d in dietary_input.split(",") if d.strip()]
    
    # Search for destination information
    destination_info = await search_destination_info(
        destination, start_date, end_date, home_location, 
        (budget_min, budget_max), currency
    )
    display_search_results(destination_info)
    
    # Confirm to proceed
    proceed = get_user_input("Ready to generate your itinerary? (yes/no)", "yes")
    if proceed.lower() not in ["yes", "y"]:
        print("\n👋 Planning cancelled. Come back anytime!")
        return
    
    # Create traveler profile
    profile = TravelerProfile(
        traveler_id=f"user-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name=name,
        email=email if email else None,
        home_location=home_location,
        preferences=TravelerPreferences(
            budget_min=Decimal(str(budget_min)),
            budget_max=Decimal(str(budget_max)),
            travel_style=travel_style,
            interests=interests,
            accessibility_needs=[],
            dietary_restrictions=dietary_restrictions,
        ),
        loyalty_programs={},
    )
    
    # Create task context with research data
    task_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    context = TaskContext(
        task_id=task_id,
        correlation_id=correlation_id,
        trace_id=trace_id,
        traveler_profile=profile,
        request_params={
            "destination": destination,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "purpose": "vacation",
            "travelers_count": 1,
            "currency": currency,
        },
        intermediate_results={
            "gemini_research": destination_info,
        },
    )
    
    # Execute workflow
    print("\n" + "=" * 80)
    print("🚀 GENERATING YOUR PERSONALIZED ITINERARY".center(80))
    print("=" * 80 + "\n")
    
    listener, adapter = create_monitoring_listener("monitoring_events.json")
    workflow = DynamicPlannerWorkflow()
    
    try:
        # Extract request params from context
        request_params = context.request_params
        
        # Create MonitoringCallbacks instance
        from src.callbacks.monitoring import MonitoringCallbacks
        callbacks = MonitoringCallbacks(
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        callbacks.register_listener(listener)
        
        itinerary = await workflow.execute(
            traveler_profile=profile,
            request_params=request_params,
            callbacks=callbacks,
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("✅ ITINERARY GENERATED SUCCESSFULLY".center(80))
        print("=" * 80 + "\n")
        
        print(f"📍 Destination: {itinerary.destination}")
        print(f"📅 Dates: {itinerary.start_date.strftime('%B %d, %Y')} - {itinerary.end_date.strftime('%B %d, %Y')}")
        print(f"💰 Total Cost: {currency} {itinerary.total_cost.total:,.2f}")
        print(f"📝 Segments: {len(itinerary.segments)}")
        
        if itinerary.optimization_notes:
            print(f"\n💡 Optimization Notes:\n{itinerary.optimization_notes}")
        
        # Save outputs with timestamps for unique filenames
        output_dir = Path("examples")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"itinerary_{destination.lower().replace(' ', '_')}_{timestamp}.json"
        md_path = output_dir / f"itinerary_{destination.lower().replace(' ', '_')}_{timestamp}.md"
        research_path = output_dir / f"research_{destination.lower().replace(' ', '_')}_{timestamp}.md"
        
        # Save JSON (include research inline)
        itinerary_json = json.loads(itinerary.model_dump_json())
        research_json = {
            "weather": destination_info.get("weather", ""),
            "accommodation": destination_info.get("accommodation", ""),
            "attractions": destination_info.get("attractions", ""),
            "estimated_daily_cost": destination_info.get("estimated_daily_cost", 0),
            "travel_tips": destination_info.get("travel_tips", ""),
            "timing_analysis": destination_info.get("best_time", ""),
        }
        combined_payload = {
            "itinerary": itinerary_json,
            "research": research_json,
            "generated_at": datetime.utcnow().isoformat(),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(combined_payload, indent=2, ensure_ascii=False))
        print(f"\n💾 JSON saved to: {json_path}")
        
        # Save Markdown (add At-a-Glance + include research summary inline)
        weather_snippet = str(destination_info.get("weather", ""))
        weather_snippet = weather_snippet[:300] + ("…" if len(weather_snippet) > 300 else "")
        # Extract up to 3 attraction names for quick highlights
        highlights_line = ""
        try:
            attr_raw = destination_info.get("attractions", "")
            attr_list = json.loads(attr_raw) if isinstance(attr_raw, str) else attr_raw
            if isinstance(attr_list, list):
                names = [a.get("name") for a in attr_list if isinstance(a, dict) and a.get("name")]
                if names:
                    highlights = ", ".join(names[:3])
                    highlights_line = f"- Highlights: {highlights}"
        except Exception:
            # Graceful fallback: no highlights
            highlights_line = ""
        md_sections = [
            "## 🔎 At-a-Glance",
            "",
            f"- Destination: {destination}",
            f"- Dates: {start_date.strftime('%B %d, %Y')} → {end_date.strftime('%B %d, %Y')}",
            f"- Origin: {home_location}",
            f"- Budget: {currency} {budget_min:,.0f} – {budget_max:,.0f}",
            f"- Est. Daily Cost: {currency} {destination_info.get('estimated_daily_cost', 0):,.0f}",
            (f"- Weather Snapshot: {weather_snippet}" if weather_snippet else ""),
            (highlights_line if highlights_line else ""),
            "",
            "---",
            "",
            itinerary.to_markdown(),
            "",
            "---",
            "",
            "## 📚 Research Summary",
        ]
        if destination_info.get("weather"):
            md_sections += ["", "### 🌤️ Weather Information", "", str(destination_info.get("weather", ""))]
        if destination_info.get("accommodation"):
            md_sections += ["", "### 🏨 Accommodation Suggestions", "", str(destination_info.get("accommodation", ""))]
        if destination_info.get("attractions"):
            md_sections += ["", "### 🎭 Top Attractions", "", str(destination_info.get("attractions", ""))]
        if destination_info.get("estimated_daily_cost") is not None:
            md_sections += ["", "### 💰 Estimated Daily Cost", "", f"{currency} {destination_info.get('estimated_daily_cost', 0):,.0f} per day"]
        if destination_info.get("travel_tips"):
            md_sections += ["", "### 💡 Travel Tips", "", str(destination_info.get("travel_tips", ""))]
        if destination_info.get("best_time"):
            md_sections += ["", "### 📅 Timing Analysis", "", str(destination_info.get("best_time", ""))]
        md_content = "\n".join(md_sections) + "\n"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"💾 Markdown saved to: {md_path}")
        
        # Save Research Results
        with open(research_path, "w", encoding="utf-8") as f:
            f.write(f"# Travel Research: {destination}\n\n")
            f.write(f"**Research Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
            f.write(f"**Destination:** {destination}\n")
            f.write(f"**Travel Dates:** {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}\n")
            f.write(f"**Budget:** {currency} {budget_min:,.0f} - {budget_max:,.0f}\n\n")
            f.write("---\n\n")
            
            f.write("## 🌤️ Weather Information\n\n")
            f.write(destination_info.get("weather", "") + "\n\n")
            
            f.write("## 🏨 Accommodation Suggestions\n\n")
            f.write(destination_info.get("accommodation", "") + "\n\n")
            
            f.write("## 🎭 Top Attractions\n\n")
            f.write(destination_info.get("attractions", "") + "\n\n")
            
            f.write("## 💰 Estimated Daily Cost\n\n")
            f.write(f"{currency} {destination_info.get('estimated_daily_cost', 0):,.0f} per day\n\n")
            
            f.write("## 💡 Travel Tips\n\n")
            f.write(destination_info.get("travel_tips", "") + "\n\n")
            
            f.write("## 📅 Best Time to Visit\n\n")
            f.write(destination_info.get("best_time", "") + "\n\n")
            
        print(f"💾 Research saved to: {research_path}")
        
        print("\n" + "=" * 80)
        print("Thank you for using AI Travel Planner! 🌟".center(80))
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Error generating itinerary: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        try:
            adapter.close()
        except Exception:
            pass


def main():
    """Main entry point."""
    try:
        asyncio.run(interactive_planning())
    except KeyboardInterrupt:
        print("\n\n👋 Planning cancelled by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
