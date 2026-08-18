import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from travel_planner.app.config import settings
from travel_planner.app.graph.state import TravelPlanState
from travel_planner.app.tools import (
    perform_web_search,
    get_destination_weather,
    allocate_budget,
    curate_recommendations,
)

logger = logging.getLogger(__name__)

# Decides which LLM client (OpenAI or Groq) to return based on configured API keys
def get_llm():
    if settings.default_llm_provider == "openai" and settings.openai_api_key:
        return ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key, temperature=0.2)
    elif settings.groq_api_key:
        return ChatGroq(model="qwen/qwen3.6-27b", api_key=settings.groq_api_key, temperature=0.2, max_tokens=4096)
    elif settings.openai_api_key:
        return ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key, temperature=0.2)
    return None

# Trims the previous itinerary to just Day headers and high-level activities.
# This prevents payload size limits (HTTP 413) on revision loops by saving 80%+ of tokens.
def extract_itinerary_skeleton(itinerary: str) -> str:
    if not itinerary:
        return ""
    
    skeleton_lines = []
    lines = itinerary.split("\n")
    for line in lines:
        line_stripped = line.strip()
        # Keep only day titles and main activities (morning/afternoon/evening)
        if line_stripped.startswith("### Day") or line_stripped.startswith("## Day") or (line_stripped.startswith("#") and "day" in line_stripped.lower()):
            skeleton_lines.append(line_stripped)
        elif line_stripped.startswith("-") and any(x in line_stripped.lower() for x in ["morning", "afternoon", "evening", "visit", "dine", "lunch", "dinner"]):
            if len(line_stripped) > 85:
                line_stripped = line_stripped[:82] + "..."
            skeleton_lines.append(line_stripped)
            
    return "\n".join(skeleton_lines)

# Node 1: Orchestrator - Validates user travel constraints and sets up initial state
def orchestrator_input(state: TravelPlanState) -> Dict[str, Any]:
    destination = state.get("destination", "").strip()
    travel_dates = state.get("travel_dates", "").strip()
    budget_range = state.get("budget_range", "Moderate").strip()
    travelers_count = state.get("travelers_count", 1)
    interests = state.get("interests", [])
    
    if not destination or not travel_dates:
        raise ValueError("Destination and travel_dates are required.")
        
    return {
        "destination": destination,
        "travel_dates": travel_dates,
        "budget_range": budget_range,
        "travelers_count": travelers_count,
        "interests": interests,
        "research_data": {},
        "draft_itinerary": "",
        "user_feedback": "",
        "feedback_status": "",
        "status": "started",
        "next_route": None
    }

# Node 2: Research Agent - Gathers coordinate-resolved weather forecasts and web search summaries
def research_agent(state: TravelPlanState) -> Dict[str, Any]:
    destination = state["destination"]
    weather_data = get_destination_weather(destination)
    search_data = perform_web_search(destination)
    
    return {
        "research_data": {
            "weather": weather_data,
            "search_brief": search_data
        },
        "status": "research_completed"
    }

# Node 3: Planner Agent - Combines inputs, allocates budgets, curates places, and generates itinerary draft
def planner_agent(state: TravelPlanState) -> Dict[str, Any]:
    destination = state["destination"]
    travel_dates = state["travel_dates"]
    budget_range = state["budget_range"]
    travelers_count = state["travelers_count"]
    interests = state["interests"]
    research_data = state["research_data"]
    user_feedback = state.get("user_feedback", "")
    
    # Calculate budget details and match interests to dining/attractions
    budget_allocation = allocate_budget(budget_range, travelers_count, travel_dates)
    curated_spots = curate_recommendations(destination, interests, budget_range)
    
    # Format a dense weather overview and final budget limits
    weather_info = research_data.get("weather", {})
    weather_brief = weather_info.get("weather_summary")
    if not weather_brief:
        clothing_tip = weather_info.get("recommendation", "pack layered attire")
        weather_brief = f"Weather: {weather_info.get('avg_min_temp_c', 12)}°C to {weather_info.get('avg_max_temp_c', 22)}°C ({clothing_tip})"
        
    resolved_name = weather_info.get("resolved_name", destination)
    search_brief = research_data.get("search_brief", "No additional insights.")
    
    budget_str = (
        f"Accommodations: ${budget_allocation['accommodation_total_usd']} USD\n"
        f"Dining: ${budget_allocation['dining_total_usd']} USD\n"
        f"Transportation: ${budget_allocation['transportation_total_usd']} USD\n"
        f"Activities: ${budget_allocation['activities_total_usd']} USD\n"
        f"Grand Total: ${budget_allocation['grand_total_usd']} USD"
    )
    
    llm = get_llm()
    if llm:
        system_prompt = (
            "You are a travel planner. Write a day-by-day itinerary matching the destination, budget, weather, and curated options."
        )
        
        interests_str = ", ".join(interests) if interests else "Sightseeing"
        curated_dining = "\n".join([f"- {d['name']} ({d['cuisine']}, {d['tier']})" for d in curated_spots.get("dining", [])])
        curated_attractions = "\n".join([f"- {a['name']} ({a['type']}): {a['description']}" for a in curated_spots.get("attractions", [])])
        
        user_prompt = (
            f"Destination: {resolved_name}\n"
            f"Dates: {travel_dates} ({budget_allocation['duration_days']} days) | Travelers: {travelers_count} | Class: {budget_range}\n"
            f"Interests: {interests_str}\n"
            f"Budget: {budget_str}\n"
            f"Weather: {weather_brief}\n"
            f"Curation Dining:\n{curated_dining}\n"
            f"Curation Attractions:\n{curated_attractions}\n"
            f"Web context:\n{search_brief}\n"
        )
        
        # If revising, attach only the structural skeleton of the previous draft to save tokens
        if user_feedback:
            skeleton = extract_itinerary_skeleton(state.get("draft_itinerary", ""))
            user_prompt += (
                f"\n--- PREVIOUS ITINERARY SKELETON ---\n{skeleton}\n"
                f"\n--- REVISION INSTRUCTION ---\nModify the plan as follows: {user_feedback}\n"
            )
            
        try:
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            draft = response.content
            import re
            draft = re.sub(r"(?is)<think>.*?</think>", "", draft).strip()
            draft = re.sub(r"(?is)<think>.*$", "", draft).strip()
            draft = re.sub(r"(?is)^thinking process:.*?\n", "", draft).strip()
            if len(draft) < 200:
                raise ValueError("LLM generated output is empty or truncated during reasoning.")
        except Exception as e:
            logger.error(f"LLM planning failed: {e}. Falling back to template plan.")
            draft = generate_template_itinerary(resolved_name, travel_dates, budget_allocation, curated_spots, weather_brief, user_feedback)
    else:
        # Fallback to local template generation if no active LLM keys are configured
        draft = generate_template_itinerary(resolved_name, travel_dates, budget_allocation, curated_spots, weather_brief, user_feedback)
        
    return {
        "draft_itinerary": draft,
        "status": "pending_review",
        "feedback_status": ""
    }

# Node 4: HITL Review - Decides whether to finalize the plan or routing for revisions
def hitl_review_node(state: TravelPlanState) -> Dict[str, Any]:
    action = state.get("feedback_status", "approve")
    feedback = state.get("user_feedback", "")
    
    if action == "approve":
        return {
            "status": "approved",
            "next_route": "finalizer"
        }
        
    # Check if the user comment requests weather/season/date updates.
    # If yes, route back to Research node; otherwise, route directly to Planner node.
    feedback_lower = feedback.lower()
    research_triggers = ["weather", "date", "days", "season", "search", "lookup", "locate", "destination", "city", "temperature", "rain", "forecast"]
    
    if any(trigger in feedback_lower for trigger in research_triggers):
        next_step = "research_agent"
    else:
        next_step = "planner_agent"
        
    return {
        "status": "revised",
        "next_route": next_step
    }

# Node 5: Finalizer - Appends final touch-ups, budget summaries, and wraps the package
def finalizer_node(state: TravelPlanState) -> Dict[str, Any]:
    destination = state["destination"]
    draft = state["draft_itinerary"]
    budget_range = state["budget_range"]
    travelers_count = state["travelers_count"]
    travel_dates = state["travel_dates"]
    
    budget_allocation = allocate_budget(budget_range, travelers_count, travel_dates)
    
    budget_summary = (
        f"\n\n### Budget Summary ({budget_allocation['budget_tier']})\n"
        f"- **Duration**: {budget_allocation['duration_days']} Days\n"
        f"- **Accommodation**: ${budget_allocation['accommodation_total_usd']:,} USD ({budget_allocation['rooms_allocated']} rooms)\n"
        f"- **Dining**: ${budget_allocation['dining_total_usd']:,} USD\n"
        f"- **Transportation**: ${budget_allocation['transportation_total_usd']:,} USD\n"
        f"- **Activities**: ${budget_allocation['activities_total_usd']:,} USD\n"
        f"- **Emergency contingency (10%)**: ${budget_allocation['emergency_fund_usd']:,} USD\n"
        f"- **Grand Total Estimated**: ${budget_allocation['grand_total_usd']:,} USD\n"
    )
    
    header = (
        f"# FINAL TRIP PLAN: {destination.upper()}\n"
        f"**Dates**: {travel_dates} | **Travelers**: {travelers_count} | **Class**: {budget_range}\n\n"
    )
    
    footer = (
        "\n\n---\n"
        "**Happy Travels!** *This itinerary has been approved and finalized. Ensure to verify bookings and opening times in advance.*"
    )
    
    return {
        "draft_itinerary": header + draft + budget_summary + footer,
        "status": "completed"
    }

# Local template generation fallback when LLM is unavailable
def generate_template_itinerary(
    destination: str,
    travel_dates: str,
    budget: Dict[str, Any],
    curated: Dict[str, Any],
    weather_brief: str,
    user_feedback: str = ""
) -> str:
    duration = budget["duration_days"]
    dining = curated.get("dining", [])
    attractions = curated.get("attractions", [])
    
    itinerary_days = []
    for day in range(1, duration + 1):
        attr_idx = (day - 1) % len(attractions) if attractions else None
        dine_idx = (day - 1) % len(dining) if dining else None
        
        attr_str = f"Visit **{attractions[attr_idx]['name']}** ({attractions[attr_idx]['type']}). {attractions[attr_idx]['description']}" if attr_idx is not None else "Sightseeing around central hub."
        dine_str = f"Dine at **{dining[dine_idx]['name']}** ({dining[dine_idx]['cuisine']})." if dine_idx is not None else "Enjoy local culinary delights."
        
        day_plan = (
            f"### Day {day}\n"
            f"- **Morning & Afternoon**: {attr_str}\n"
            f"- **Evening**: {dine_str}\n"
            f"- **Transport Tip**: Utilize recommended transit modes."
        )
        itinerary_days.append(day_plan)
        
    days_combined = "\n\n".join(itinerary_days)
    
    feedback_section = ""
    if user_feedback:
        feedback_section = f"\n\n*(Incorporate feedback log: Adjusted plan based on instructions: '{user_feedback}')*\n\n"
        
    return (
        f"### Day-by-Day Itinerary\n"
        f"{weather_brief}\n\n"
        f"{feedback_section}"
        f"{days_combined}"
    )
