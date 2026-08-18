import streamlit as st
import uuid
import json
from travel_planner.app.graph.workflow import travel_planner_workflow
from travel_planner.app.tools import allocate_budget

# Set page configuration
st.set_page_config(
    page_title="Stateful AI Travel Planner Dashboard",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 Stateful AI Travel Planner Dashboard")
st.markdown("An interactive multi-agent stateful travel planner using LangGraph and FastAPI with Human-in-the-Loop approval.")

# Initialize session state variables
if "plan_id" not in st.session_state:
    st.session_state.plan_id = None
if "graph_values" not in st.session_state:
    st.session_state.graph_values = {}
if "execution_logs" not in st.session_state:
    st.session_state.execution_logs = []

# Sidebar configurations
with st.sidebar:
    st.header("Settings & Keys")
    st.write(f"**Default LLM Provider:** `{st.session_state.get('llm_provider', 'groq')}`")
    
    # Check key configurations in environment settings
    from travel_planner.app.config import settings
    groq_configured = "Configured ✅" if settings.groq_api_key else "Missing ❌"
    serper_configured = "Configured ✅" if settings.serper_api_key else "Missing ❌"
    
    st.write(f"**Groq API Key:** {groq_configured}")
    st.write(f"**Serper API Key:** {serper_configured}")
    
    st.divider()
    if st.button("Reset Session State", type="secondary"):
        st.session_state.plan_id = None
        st.session_state.graph_values = {}
        st.session_state.execution_logs = []
        st.rerun()

# Define UI tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🛫 Planner Workspace", 
    "🔍 Internal State Inspector", 
    "📊 External Research Insights",
    "💸 Budget Calculations"
])

# ============================================================
# TAB 1: PLANNER WORKSPACE (External & HITL UI)
# ============================================================
with tab1:
    st.header("Travel Planner Console")
    
    if not st.session_state.plan_id:
        st.subheader("1. Enter Travel Details")
        col1, col2 = st.columns(2)
        with col1:
            destination = st.text_input("Destination", value="Paris")
            travel_dates = st.text_input("Dates (YYYY-MM-DD to YYYY-MM-DD)", value="2026-09-10 to 2026-09-15")
            budget_range = st.selectbox("Budget Class", ["Moderate", "Economy", "Luxury"], index=0)
        with col2:
            travelers = st.number_input("Number of Travelers", min_value=1, value=2)
            interests = st.text_input("Interests (comma separated)", value="museums, romance, art")
            
        if st.button("Generate Initial Itinerary Draft", type="primary"):
            plan_id = str(uuid.uuid4())
            st.session_state.plan_id = plan_id
            st.session_state.execution_logs = []
            
            # Setup initial state values
            initial_state = {
                "destination": destination,
                "travel_dates": travel_dates,
                "budget_range": budget_range,
                "travelers_count": travelers,
                "interests": [i.strip() for i in interests.split(",") if i.strip()],
                "research_data": {},
                "draft_itinerary": "",
                "user_feedback": "",
                "feedback_status": "",
                "status": "started"
            }
            
            st.session_state.execution_logs.append("Executing Node: `orchestrator_input`")
            st.session_state.execution_logs.append("Executing Node: `research_agent`")
            st.session_state.execution_logs.append("Executing Node: `planner_agent` (LLM call)")
            st.session_state.execution_logs.append("Checkpoint Interrupt: Awaiting HITL user review")
            
            with st.spinner("Executing travel planner multi-agent workflow..."):
                config = {"configurable": {"thread_id": plan_id}}
                travel_planner_workflow.invoke(initial_state, config)
                
                # Fetch checkpoint state
                state_snapshot = travel_planner_workflow.get_state(config)
                st.session_state.graph_values = state_snapshot.values
            st.rerun()
            
    else:
        st.subheader(f"Current Plan ID: `{st.session_state.plan_id}`")
        values = st.session_state.graph_values
        current_status = values.get("status", "pending_review")
        
        # Display Execution Log Traces
        st.info(" | ".join(st.session_state.execution_logs))
        
        if current_status == "completed":
            st.success("Plan Approved and Finalized!")
            st.markdown(values.get("draft_itinerary", ""))
            
            if st.button("Create a New Plan"):
                st.session_state.plan_id = None
                st.session_state.graph_values = {}
                st.session_state.execution_logs = []
                st.rerun()
        else:
            st.subheader("Draft Itinerary (Awaiting Approval)")
            st.markdown(values.get("draft_itinerary", ""))
            
            if st.checkbox("Show Raw Text / Metadata Details"):
                st.text_area("Raw Text Itinerary Output", value=values.get("draft_itinerary", ""), height=250)
                st.json(values)
            
            st.divider()
            st.subheader("User Review / HITL Interaction")
            
            feedback_text = st.text_area("Provide feedback or request changes here:", value="")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Approve & Finalize Plan", type="primary"):
                    config = {"configurable": {"thread_id": st.session_state.plan_id}}
                    st.session_state.execution_logs.append("User Approved plan.")
                    st.session_state.execution_logs.append("Executing Node: `hitl_review_node` (Routing to finalizer)")
                    st.session_state.execution_logs.append("Executing Node: `finalizer_node`")
                    st.session_state.execution_logs.append("Workflow Completed Successfully.")
                    
                    with st.spinner("Finalizing trip package..."):
                        travel_planner_workflow.update_state(
                            config, 
                            {
                                "feedback_status": "approve", 
                                "user_feedback": "Approved via UI."
                            }
                        )
                        travel_planner_workflow.invoke(None, config)
                        
                        state_snapshot = travel_planner_workflow.get_state(config)
                        st.session_state.graph_values = state_snapshot.values
                    st.rerun()
                    
            with col_btn2:
                if st.button("Request Modifications", type="secondary"):
                    if not feedback_text.strip():
                        st.warning("Please provide feedback comments before requesting modifications.")
                    else:
                        config = {"configurable": {"thread_id": st.session_state.plan_id}}
                        st.session_state.execution_logs.append(f"User requested changes: '{feedback_text}'")
                        
                        # Decide routing path log
                        feedback_lower = feedback_text.lower()
                        research_triggers = ["weather", "date", "days", "season", "search", "lookup", "locate", "destination", "city", "temperature", "rain", "forecast"]
                        if any(trigger in feedback_lower for trigger in research_triggers):
                            st.session_state.execution_logs.append("Executing Node: `hitl_review_node` (Routing to research)")
                            st.session_state.execution_logs.append("Executing Node: `research_agent`")
                        else:
                            st.session_state.execution_logs.append("Executing Node: `hitl_review_node` (Routing to planner)")
                            
                        st.session_state.execution_logs.append("Executing Node: `planner_agent` (LLM call with skeleton history)")
                        st.session_state.execution_logs.append("Checkpoint Interrupt: Awaiting HITL user review")
                        
                        with st.spinner("Re-executing workflow with feedback..."):
                            travel_planner_workflow.update_state(
                                config, 
                                {
                                    "feedback_status": "modify", 
                                    "user_feedback": feedback_text
                                }
                            )
                            travel_planner_workflow.invoke(None, config)
                            
                            state_snapshot = travel_planner_workflow.get_state(config)
                            st.session_state.graph_values = state_snapshot.values
                        st.rerun()

# ============================================================
# TAB 2: INTERNAL STATE INSPECTOR
# ============================================================
with tab2:
    st.header("State persistence - JSON State Checkpoint Dump")
    st.markdown("This shows the actual live state contents inside the LangGraph checkpointer thread memory.")
    if st.session_state.graph_values:
        st.json(st.session_state.graph_values)
    else:
        st.info("No plan generated yet. Generate an initial plan to inspect state.")

# ============================================================
# TAB 3: EXTERNAL RESEARCH INSIGHTS
# ============================================================
with tab3:
    st.header("External Tools Data Integration")
    if st.session_state.graph_values:
        research = st.session_state.graph_values.get("research_data", {})
        
        st.subheader("1. Open-Meteo Weather Insights")
        st.json(research.get("weather", {}))
        
        st.subheader("2. Web Search Snippets (Serper / Tavily)")
        st.write(research.get("search_brief", "No web search data available."))
    else:
        st.info("No plan generated yet. Generate an initial plan to inspect external tool datasets.")

# ============================================================
# TAB 4: BUDGET CALCULATIONS
# ============================================================
with tab4:
    st.header("Deterministic Budget Allocations")
    if st.session_state.graph_values:
        values = st.session_state.graph_values
        budget_range = values.get("budget_range", "Moderate")
        travelers = values.get("travelers_count", 2)
        dates = values.get("travel_dates", "")
        
        allocation = allocate_budget(budget_range, travelers, dates)
        
        st.subheader(f"Cost Breakdown for {travelers} travelers over {dates}")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.metric("Accommodations", f"${allocation['accommodation_total_usd']} USD")
        with col_c2:
            st.metric("Dining", f"${allocation['dining_total_usd']} USD")
        with col_c3:
            st.metric("Transportation", f"${allocation['transportation_total_usd']} USD")
        with col_c4:
            st.metric("Activities", f"${allocation['activities_total_usd']} USD")
            
        st.divider()
        st.metric("Grand Total Estimated (including 10% contingency)", f"${allocation['grand_total_usd']} USD")
        st.json(allocation)
    else:
        st.info("No plan generated yet. Generate an initial plan to inspect budget tool calculations.")
