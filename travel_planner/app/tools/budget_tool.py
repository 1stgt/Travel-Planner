from datetime import datetime
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def parse_duration_days(travel_dates: str) -> int:
    try:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", travel_dates)
        if len(dates) == 2:
            d1 = datetime.strptime(dates[0], "%Y-%m-%d")
            d2 = datetime.strptime(dates[1], "%Y-%m-%d")
            delta = d2 - d1
            return max(1, delta.days)
    except Exception as e:
        logger.warning(f"Could not parse duration from dates '{travel_dates}': {e}. Using default of 5 days.")
    return 5

def allocate_budget(budget_range: str, travelers_count: int, travel_dates: str) -> Dict[str, Any]:
    duration_days = parse_duration_days(travel_dates)
    tier = budget_range.strip().lower()
    
    if "economy" in tier:
        daily_room_rate = 60.0
        daily_dining_rate = 30.0
        daily_transport_rate = 15.0
        daily_activities_rate = 20.0
    elif "luxury" in tier:
        daily_room_rate = 450.0
        daily_dining_rate = 220.0
        daily_transport_rate = 120.0
        daily_activities_rate = 150.0
    else:
        daily_room_rate = 160.0
        daily_dining_rate = 85.0
        daily_transport_rate = 45.0
        daily_activities_rate = 60.0

    rooms_needed = max(1, (travelers_count + 1) // 2)
    
    accommodation_total = daily_room_rate * rooms_needed * duration_days
    dining_total = daily_dining_rate * travelers_count * duration_days
    transportation_total = daily_transport_rate * travelers_count * duration_days
    activities_total = daily_activities_rate * travelers_count * duration_days
    
    subtotal = accommodation_total + dining_total + transportation_total + activities_total
    emergency_fund = round(subtotal * 0.10, 2)
    grand_total = subtotal + emergency_fund
    
    return {
        "budget_tier": budget_range,
        "duration_days": duration_days,
        "travelers_count": travelers_count,
        "rooms_allocated": rooms_needed,
        "accommodation_total_usd": round(accommodation_total, 2),
        "dining_total_usd": round(dining_total, 2),
        "transportation_total_usd": round(transportation_total, 2),
        "activities_total_usd": round(activities_total, 2),
        "emergency_fund_usd": emergency_fund,
        "grand_total_usd": round(grand_total, 2)
    }
