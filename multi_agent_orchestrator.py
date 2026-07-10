import os
import sys
import requests
import time
from smolagents import CodeAgent, DuckDuckGoSearchTool, tool

# --- TOKEN VALIDATION (CTO Guardrail) ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ARCHITECTURE ERROR] GEMINI_API_KEY is missing!")
    print("Please set your Gemini token in the terminal before running.")
    print("Example in PowerShell: $env:GEMINI_API_KEY='your_actual_token_here'\n")
    sys.exit(1)

# The active Go server endpoint
GO_API_URL = "http://localhost:8080/api/allocate"

# --- 1. SCHEDULING TOOLS (Domain: Direct Go API Transactions) ---
@tool
def check_and_execute_go_allocation(course_code: str, room_code: str, faculty_id: str, timeslot_id: str) -> str:
    """Attempts to allocate an exam room and a proctor directly via the high-performance Go backend API.
    Args:
        course_code: The identifier code of the course (e.g., 'PHY101').
        room_code: The classroom identifier (e.g., 'R102').
        faculty_id: The professor's payroll identifier (e.g., 'FAC01').
        timeslot_id: The target scheduling session (e.g., 'MON_FN').
    """
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

# --- 2. MODEL INITIALIZATION (Pivoted to Gemini to bypass HF Rate Limits) ---
# We use LiteLLM to bind smolagents directly to Google's fast, free-tier gemini-2.5-flash
try:
    from smolagents import LiteLLMModel
except ImportError:
    print("[Error] LiteLLM library is missing. Install with: pip install 'smolagents[litellm]'")
    sys.exit(1)

model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.1,
    max_tokens=2048,
    num_retries=3
)

# --- 3. WORKER AGENT A: The Web Researcher ---
research_agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
    name="web_researcher",
    description="Searches the internet for real-world data and context.",
    max_steps=3
)

# --- 4. WORKER AGENT B: The Institutional Scheduler ---
scheduler_agent = CodeAgent(
    model=model,
    tools=[check_and_execute_go_allocation],
    name="academic_scheduler",
    description=(
        "Manages direct university database allocations via the Go server. "
        "IMPORTANT: You are a CodeAgent. Optimize your API calls by checking room configurations "
        "and immediately resolving fallbacks in a single python block."
    ),
    max_steps=5
)

# --- 5. EXPLICIT DELEGATION ADAPTERS (Bypassing Framework Bugs) ---
@tool
def delegate_to_researcher(query: str) -> str:
    """Delegates a task to the Web Researcher agent to search the internet for external knowledge.
    Args:
        query: The detailed research request or question to ask the sub-agent.
    """
    print(f"\n[ORCHESTRATOR DELEGATION] -> Routing to Web Researcher: '{query}'")
    time.sleep(1) # Defensive delay to prevent Gemini rate limit exceptions
    return str(research_agent.run(query))

@tool
def delegate_to_scheduler(query: str) -> str:
    """Delegates a scheduling and database task to the Academic Scheduler agent. 
    You MUST pass all details including fallback options inside this query string.
    Args:
        query: The detailed scheduling request, including fallback rooms if primary choices fail.
    """
    print(f"\n[ORCHESTRATOR DELEGATION] -> Routing to Academic Scheduler: '{query}'")
    time.sleep(1) # Defensive delay to prevent Gemini rate limit exceptions
    return str(scheduler_agent.run(query))

# --- 6. THE ORCHESTRATOR: The Manager Agent ---
manager_agent = CodeAgent(
    model=model,
    tools=[delegate_to_researcher, delegate_to_scheduler],
    additional_authorized_imports=["time"],
    max_steps=5
)

if __name__ == "__main__":
    complex_task = (
        "I am an administrator. First, find out the current CEO of Google so I can include it in "
        "my exam question paper header. Then, attempt to schedule the PHY101 exam in Room R102 "
        "with Prof. Sarah (FAC01) for Monday Forenoon (MON_FN). If Room R102 returns a conflict, "
        "instruct the scheduler to fall back to Room R101."
    )
    
    print("\n[INITIATING HIERARCHICAL ORCHESTRATION WITH GO API INTEGRATION]")
    manager_agent.run(complex_task)