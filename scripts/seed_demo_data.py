"""
Seed demo data script.

Populates the database with sample data for testing and demonstration.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.state.store import get_state_store
from src.logging.json_logger import get_logger

logger = get_logger(__name__)


async def seed_demo_data() -> None:
    """Seed demo data into the state store."""
    logger.info("Seeding demo data...")
    
    state_store = await get_state_store()
    
    # Sample flight data
    sample_flights = [
        {
            "id": "demo-flight-1",
            "provider": "SkyAirlines",
            "origin": "SFO",
            "destination": "BCN",
            "price": 550.00,
        },
        {
            "id": "demo-flight-2",
            "provider": "GlobalAir",
            "origin": "SFO",
            "destination": "BCN",
            "price": 620.00,
        },
    ]
    
    await state_store.set("demo:flights", sample_flights)
    
    # Sample hotel data
    sample_hotels = [
        {
            "id": "demo-hotel-1",
            "name": "Barcelona Downtown Hotel",
            "price_per_night": 150.00,
            "rating": 4.5,
        },
        {
            "id": "demo-hotel-2",
            "name": "Seaside Resort",
            "price_per_night": 220.00,
            "rating": 4.8,
        },
    ]
    
    await state_store.set("demo:hotels", sample_hotels)
    
    # Sample activities
    sample_activities = [
        {
            "id": "demo-activity-1",
            "name": "Sagrada Familia Tour",
            "price": 45.00,
            "duration": 3,
        },
        {
            "id": "demo-activity-2",
            "name": "Park Güell Visit",
            "price": 30.00,
            "duration": 2,
        },
    ]
    
    await state_store.set("demo:activities", sample_activities)
    
    logger.info("Demo data seeded successfully")
    logger.info(f"- {len(sample_flights)} flights")
    logger.info(f"- {len(sample_hotels)} hotels")
    logger.info(f"- {len(sample_activities)} activities")


async def clear_demo_data() -> None:
    """Clear demo data from the state store."""
    logger.info("Clearing demo data...")
    
    state_store = await get_state_store()
    
    await state_store.delete("demo:flights")
    await state_store.delete("demo:hotels")
    await state_store.delete("demo:activities")
    
    logger.info("Demo data cleared")


async def main() -> None:
    """Main entry point."""
    import sys
    
    logger.info("Demo data seed script")
    
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        await clear_demo_data()
    else:
        await seed_demo_data()
    
    logger.info("Script complete")


if __name__ == "__main__":
    asyncio.run(main())
