from typing import TypedDict, List, Dict, Any, Optional, Literal

class TravelPlanState(TypedDict):
    destination: str
    travel_dates: str
    budget_range: str
    travelers_count: int
    interests: List[str]
    
    research_data: Dict[str, Any]
    draft_itinerary: str
    user_feedback: str
    feedback_status: Literal["approve", "reject", "modify", ""]
    status: str
    
    next_route: Optional[str]
