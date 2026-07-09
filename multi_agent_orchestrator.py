import os
import sys
import yaml
import time
from smolagents import CodeAgent, DuckDuckGoSearchTool, tool, LiteLLMModel

# --- TOKEN VALIDATION (CTO Guardrail) ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ARCHITECTURE ERROR] GEMINI_API_KEY is missing!")
    print("Please set your Gemini token in the terminal before running.")
    print("Example in PowerShell: $env:GEMINI_API_KEY='your_actual_token_here'\n")
    sys.exit(1)

# --- 1. MOCK DATABASE (To be replaced by Go Backend in Unit 3) ---
ROOM_DATABASE = {
    "R101": {"capacity": 30, "booked_slots": []},
    "R102": {"capacity": 40, "booked_slots": ["MON_FN"]}, 
}
FACULTY_DATABASE = {
    "FAC01": {"name": "Prof. Sarah", "assigned_slots": [], "max_duty_ceiling": 3},
    "FAC02": {"name": "Prof. Ratan", "assigned_slots": ["MON_FN"], "max_duty_ceiling": 3} 
}

# --- 2. SCHEDULING TOOLS (Domain: Academic Operations) ---
@tool
def check_room_availability(room_code: str, timeslot_id: str) -> str:
    """Validates if a classroom is free and returns its seating capacity.
    Args:
        room_code: The identifier code of the classroom (e.g., 'R101').
        timeslot_id: The target exam session slot (e.g., 'MON_FN').
    """
    code, slot = room_code.strip().upper(), timeslot_id.strip().upper()
    if code not in ROOM_DATABASE: return f"Error: Room {code} not found."
    if slot in ROOM_DATABASE[code]["booked_slots"]: return f"Conflict: {code} is booked during {slot}."
    return f"Available: {code} is free. Capacity: {ROOM_DATABASE[code]['capacity']}."

@tool
def verify_proctor_eligibility(faculty_id: str, timeslot_id: str) -> str:
    """Validates if an invigilator is free and under their duty limits.
    Args:
        faculty_id: The identifier for the professor (e.g., 'FAC01').
        timeslot_id: The target exam session slot (e.g., 'MON_FN').
    """
    fac_id, slot = faculty_id.strip().upper(), timeslot_id.strip().upper()
    if fac_id not in FACULTY_DATABASE: return f"Error: Faculty {fac_id} not found."
    fac = FACULTY_DATABASE[fac_id]
    if slot in fac["assigned_slots"]: return f"Conflict: {fac['name']} is busy during {slot}."
    return f"Eligible: {fac['name']} is available."

@tool
def execute_exam_allocation(course_code: str, room_code: str, faculty_id: str, timeslot_id: str) -> str:
    """Commits a safe exam scheduling allocation to the academic records database.
    Args:
        course_code: Course being examined (e.g., 'PHY101').
        room_code: The validated classroom code (e.g., 'R101').
        faculty_id: The eligible proctor code (e.g., 'FAC01').
        timeslot_id: Target scheduling slot (e.g., 'MON_FN').
    """
    c_code, r_code, f_code, slot = course_code.upper(), room_code.upper(), faculty_id.upper(), timeslot_id.upper()
    ROOM_DATABASE[r_code]["booked_slots"].append(slot)
    FACULTY_DATABASE[f_code]["assigned_slots"].append(slot)
    return f"Transaction Success: {c_code} scheduled in {r_code} with {f_code} for {slot}."

# --- 3. MODEL INITIALIZATION (Pivoted to Gemini to bypass HF Rate Limits) ---
model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.2,
    max_tokens=2048,
    num_retries=3  # Automatically absorb and retry transient 429 rate limit errors
)

# --- 4. WORKER AGENT A: The Web Researcher ---
research_agent = CodeAgent(
    model=model,
    tools=[DuckDuckGoSearchTool()],
    name="web_researcher",
    description="Searches the internet for real-world data.",
    max_steps=3
)

# --- 5. WORKER AGENT B: The Institutional Scheduler ---
scheduler_agent = CodeAgent(
    model=model,
    tools=[check_room_availability, verify_proctor_eligibility, execute_exam_allocation],
    name="academic_scheduler",
    description=(
        "Manages university database operations securely. "
        "IMPORTANT: You are a CodeAgent. Optimize your API usage by writing multi-line Python scripts. "
        "Check room availability, verify proctor eligibility, and execute allocations in a SINGLE step using standard Python if/else logic."
    ),
    max_steps=5
)

# --- 6. EXPLICIT DELEGATION ADAPTERS (Bypassing Framework Bugs) ---
@tool
def delegate_to_researcher(query: str) -> str:
    """Delegates a task to the Web Researcher agent to search the internet for external knowledge, names, or financial data.
    Args:
        query: The detailed research request or question to ask the sub-agent.
    """
    print(f"\n[ORCHESTRATOR DELEGATION] -> Routing to Web Researcher: '{query}'")
    time.sleep(2) # Network throttle to prevent Gemini 15 RPM free-tier limits
    return str(research_agent.run(query))

@tool
def delegate_to_scheduler(query: str) -> str:
    """Delegates a task to the Academic Scheduler agent. 
    You MUST pass all fallback rooms and conditional logic into this query string so the scheduler can handle failures autonomously.
    Args:
        query: The detailed scheduling request, including any required fallback rooms or secondary proctors.
    """
    print(f"\n[ORCHESTRATOR DELEGATION] -> Routing to Academic Scheduler: '{query}'")
    time.sleep(2) # Network throttle to prevent Gemini 15 RPM free-tier limits
    return str(scheduler_agent.run(query))

# --- 7. THE ORCHESTRATOR: The Manager Agent ---
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
        "with Prof. Sarah (FAC01) for Monday Forenoon (MON_FN). If the room is booked, fall back to R101."
    )
    
    print("\n[INITIATING HIERARCHICAL ORCHESTRATION]")
    manager_agent.run(complex_task)