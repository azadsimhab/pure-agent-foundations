import os
import sys
from typing import TypedDict, Annotated
from smolagents import CodeAgent, DuckDuckGoSearchTool, tool

# --- RESILIENT MODEL IMPORTS ---
try:
    from smolagents import LiteLLMModel
except ImportError:
    print("[Error] LiteLLM library is missing. Install with: pip install 'smolagents[litellm]'")
    sys.exit(1)

# --- LANGGRAPH IMPORTS ---
try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("\n[Dependency Notice] Installing 'langgraph' extra...")
    os.system("pip install langgraph")
    from langgraph.graph import StateGraph, START, END

# --- TOKEN VALIDATION (CTO Guardrail) ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ARCHITECTURE ERROR] GEMINI_API_KEY is missing!")
    print("Example in PowerShell: $env:GEMINI_API_KEY='your_actual_token_here'\n")
    sys.exit(1)

# The active Go server endpoint
GO_API_URL = "http://localhost:8080/api/allocate"

# --- 1. SCHEDULING TOOLS (Direct Go API Transactions) ---
@tool
def check_and_execute_go_allocation(course_code: str, room_code: str, faculty_id: str, timeslot_id: str) -> str:
    """Attempts to allocate an exam room and a proctor directly via the high-performance Go backend API.
    Args:
        course_code: The identifier code of the course (e.g., 'PHY101').
        room_code: The classroom identifier (e.g., 'R102').
        faculty_id: The professor's payroll identifier (e.g., 'FAC01').
        timeslot_id: The target scheduling session (e.g., 'MON_FN').
    """
    import requests
    payload = {
        "exam_code": course_code.strip().upper(),
        "room_code": room_code.strip().upper(),
        "timeslot_id": timeslot_id.strip().upper(),
        "professor_id": faculty_id.strip().upper()
    }
    
    print(f"\n[Go API Call] Checking & allocating on Go Server: {payload}")
    
    try:
        response = requests.post(GO_API_URL, json=payload, timeout=5)
        body = response.json()
        
        if response.status_code == 200:
            return f"Success: Go backend locked transaction. Detail: {body.get('message')}"
        elif response.status_code == 409:
            return f"Conflict Detected: Go backend blocked scheduling. Reason: {body.get('message')}"
        else:
            return f"Error: Go backend returned status {response.status_code}. Detail: {body}"
            
    except requests.exceptions.ConnectionError:
        return (
            "Network Connection Failure: Unable to connect to the Go Scheduling Backend at localhost:8080. "
            "Ensure 'go run backend/main.go' is actively running in your other terminal window."
        )

# --- 2. BIND MODEL ENGINE ---
model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.1,
    max_tokens=2048,
    num_retries=3
)

# --- 3. WORKER AGENTS (The Functional Nodes) ---
research_agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
    name="web_researcher",
    description="Searches the internet for real-world data and context.",
    max_steps=3
)

scheduler_agent = CodeAgent(
    model=model,
    tools=[check_and_execute_go_allocation],
    name="academic_scheduler",
    description="Manages direct university database allocations via the Go server.",
    max_steps=5
)

# --- 4. LANGGRAPH STATE DEFINITION ---
class AgentState(TypedDict):
    task: str
    google_ceo: str
    scheduling_result: str
    final_output: str

# --- 5. LANGGRAPH NODES (Stateful Graph Functions) ---

def research_node(state: AgentState) -> dict:
    """Executes the research step using our isolated web sub-agent."""
    print("\n[LANGGRAPH NODE] ---> Entering Research Node")
    query = "Find the current CEO of Google."
    ceo_result = str(research_agent.run(query))
    print(f"[LANGGRAPH NODE] ---> Research Result: {ceo_result}")
    return {"google_ceo": ceo_result}

def scheduling_node(state: AgentState) -> dict:
    """Executes the scheduling step by interacting with the Go Backend."""
    print("\n[LANGGRAPH NODE] ---> Entering Scheduling Node")
    
    # We pass the instruction with built-in fallback rules directly to our scheduler sub-agent
    scheduler_query = (
        "Schedule the PHY101 exam in Room R102 with Prof. Sarah (FAC01) for Monday Forenoon (MON_FN). "
        "If Room R102 returns a conflict, fall back and book Room R101 instead."
    )
    result = str(scheduler_agent.run(scheduler_query))
    print(f"[LANGGRAPH NODE] ---> Scheduling Result: {result}")
    return {"scheduling_result": result}

def output_node(state: AgentState) -> dict:
    """Consolidates states and formats the finalized output."""
    print("\n[LANGGRAPH NODE] ---> Entering Output Node")
    final_summary = (
        f"--- UNIFIED ADMINISTRATION REPORT ---\n"
        f"• Verified Google CEO: {state.get('google_ceo')}\n"
        f"• Scheduling Transaction: {state.get('scheduling_result')}\n"
    )
    return {"final_output": final_summary}

# --- 6. COMPILE THE STATEGRAPH ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("research", research_node)
workflow.add_node("scheduling", scheduling_node)
workflow.add_node("output", output_node)

# Set Entry Point and Define Sequential Edges (Static Routing Flow)
workflow.add_edge(START, "research")
workflow.add_edge("research", "scheduling")
workflow.add_edge("scheduling", "output")
workflow.add_edge("output", END)

# Compile Graph
graph = workflow.compile()

# --- 7. RUN THE SYSTEM ---
if __name__ == "__main__":
    task_input = (
        "Retrieve the Google CEO and schedule the PHY101 exam."
    )
    
    initial_state = {
        "task": task_input,
        "google_ceo": "",
        "scheduling_result": "",
        "final_output": ""
    }
    
    print("\n[LANGGRAPH SYSTEM INITIALIZATION] Running stateful orchestration graph...")
    final_state = graph.invoke(initial_state)
    
    print("\n" + "="*50)
    print(final_state["final_output"])
    print("="*50)