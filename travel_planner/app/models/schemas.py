from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel

class PlanRequest(BaseModel):
    destination: str
    travel_dates: str
    budget_range: str
    travelers_count: int
    interests: List[str]

class PlanResponse(BaseModel):
    plan_id: str
    status: str

class ReviewRequest(BaseModel):
    action: Literal["approve", "reject", "modify"]
    feedback: str = ""

class PlanStatusResponse(BaseModel):
    plan_id: str
    status: str
    destination: str
    travel_dates: str
    budget_range: str
    travelers_count: int
    interests: List[str]
    research_data: Optional[Dict[str, Any]] = None
    draft_itinerary: Optional[str] = None
    user_feedback: Optional[str] = None
    feedback_status: Optional[str] = None

class FinalPlanResponse(BaseModel):
    plan_id: str
    final_itinerary: str
