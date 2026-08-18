import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from travel_planner.app.graph.state import TravelPlanState
from travel_planner.app.graph.agents import (
    orchestrator_input,
    research_agent,
    planner_agent,
    hitl_review_node,
    finalizer_node,
)

logger = logging.getLogger(__name__)

def route_after_review(state: TravelPlanState) -> Literal["research_agent", "planner_agent", "finalizer_node"]:
    next_step = state.get("next_route")
    logger.info(f"Routing after review: {next_step}")
    
    if next_step == "research_agent":
        return "research_agent"
    elif next_step == "planner_agent":
        return "planner_agent"
    else:
        return "finalizer_node"

def build_workflow():
    builder = StateGraph(TravelPlanState)
    
    builder.add_node("orchestrator_input", orchestrator_input)
    builder.add_node("research_agent", research_agent)
    builder.add_node("planner_agent", planner_agent)
    builder.add_node("hitl_review_node", hitl_review_node)
    builder.add_node("finalizer_node", finalizer_node)
    
    builder.add_edge(START, "orchestrator_input")
    builder.add_edge("orchestrator_input", "research_agent")
    builder.add_edge("research_agent", "planner_agent")
    builder.add_edge("planner_agent", "hitl_review_node")
    
    builder.add_conditional_edges(
        "hitl_review_node",
        route_after_review,
        {
            "research_agent": "research_agent",
            "planner_agent": "planner_agent",
            "finalizer_node": "finalizer_node"
        }
    )
    
    builder.add_edge("finalizer_node", END)
    
    memory = MemorySaver()
    compiled_graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["hitl_review_node"]
    )
    
    return compiled_graph

travel_planner_workflow = build_workflow()
