from fastapi import FastAPI, HTTPException, Path, status
import uuid
import logging
from travel_planner.app.models.schemas import (
    PlanRequest,
    PlanResponse,
    ReviewRequest,
    PlanStatusResponse,
    FinalPlanResponse,
)
from travel_planner.app.graph.workflow import travel_planner_workflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Travel Planner API",
    description="A multi-agent stateful travel planner using LangGraph and FastAPI with Human-in-the-Loop approval.",
    version="1.0.0"
)

@app.post("/plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(request: PlanRequest):
    plan_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": plan_id}}
    
    initial_state = {
        "destination": request.destination,
        "travel_dates": request.travel_dates,
        "budget_range": request.budget_range,
        "travelers_count": request.travelers_count,
        "interests": request.interests,
        "research_data": {},
        "draft_itinerary": "",
        "user_feedback": "",
        "feedback_status": "",
        "status": "started"
    }
    
    logger.info(f"Starting planning workflow for plan_id={plan_id} to {request.destination}")
    
    try:
        travel_planner_workflow.invoke(initial_state, config)
        state_snapshot = travel_planner_workflow.get_state(config)
        is_paused = len(state_snapshot.next) > 0 and "hitl_review_node" in state_snapshot.next[0]
        
        return PlanResponse(
            plan_id=plan_id,
            status="pending_review" if is_paused else "started"
        )
    except Exception as e:
        logger.exception(f"Error starting workflow for plan_id={plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize travel plan: {str(e)}"
        )

@app.get("/plan/{id}", response_model=PlanStatusResponse)
def get_plan_status(id: str = Path(..., description="The unique plan ID")):
    config = {"configurable": {"thread_id": id}}
    state_snapshot = travel_planner_workflow.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Travel plan with ID {id} not found."
        )
        
    values = state_snapshot.values
    is_paused = len(state_snapshot.next) > 0 and "hitl_review_node" in state_snapshot.next[0]
    current_status = "pending_review" if is_paused else values.get("status", "unknown")
    
    return PlanStatusResponse(
        plan_id=id,
        status=current_status,
        destination=values.get("destination", ""),
        travel_dates=values.get("travel_dates", ""),
        budget_range=values.get("budget_range", ""),
        travelers_count=values.get("travelers_count", 1),
        interests=values.get("interests", []),
        research_data=values.get("research_data"),
        draft_itinerary=values.get("draft_itinerary"),
        user_feedback=values.get("user_feedback"),
        feedback_status=values.get("feedback_status")
    )

@app.post("/plan/{id}/review", response_model=PlanResponse)
def submit_plan_review(
    id: str = Path(..., description="The unique plan ID"),
    review: ReviewRequest = None
):
    if review is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review payload is required.")
        
    config = {"configurable": {"thread_id": id}}
    state_snapshot = travel_planner_workflow.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Travel plan with ID {id} not found."
        )
        
    if len(state_snapshot.next) == 0 or "hitl_review_node" not in state_snapshot.next[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Travel plan {id} is not awaiting review. Current status: {state_snapshot.values.get('status')}."
        )
        
    logger.info(f"Submitting review for plan {id}: Action={review.action}, Feedback='{review.feedback}'")
    
    try:
        travel_planner_workflow.update_state(
            config,
            {
                "user_feedback": review.feedback,
                "feedback_status": review.action
            }
        )
        travel_planner_workflow.invoke(None, config)
        
        new_state_snapshot = travel_planner_workflow.get_state(config)
        new_paused = len(new_state_snapshot.next) > 0 and "hitl_review_node" in new_state_snapshot.next[0]
        new_status = "pending_review" if new_paused else new_state_snapshot.values.get("status", "unknown")
        
        return PlanResponse(
            plan_id=id,
            status=new_status
        )
    except Exception as e:
        logger.exception(f"Error processing review for plan_id={id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review and resume planning: {str(e)}"
        )

@app.get("/plan/{id}/final", response_model=FinalPlanResponse)
def get_final_plan(id: str = Path(..., description="The unique plan ID")):
    config = {"configurable": {"thread_id": id}}
    state_snapshot = travel_planner_workflow.get_state(config)
    
    if not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Travel plan with ID {id} not found."
        )
        
    values = state_snapshot.values
    current_status = values.get("status", "")
    
    if current_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Travel plan is not finalized. Current status: {current_status}. Please review and approve the draft plan first."
        )
        
    return FinalPlanResponse(
        plan_id=id,
        final_itinerary=values.get("draft_itinerary", "")
    )
