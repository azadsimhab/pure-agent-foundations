import os
import sys
import requests
from smolagents import CodeAgent, LiteLLMModel, tool

gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ERROR] GEMINI_API_KEY is missing from your environment variables!")
    print("Please run: $env:GEMINI_API_KEY='your_key_here' in your terminal.")
    sys.exit(1)

# Initialize the Gemini model via LiteLLMModel wrapper (utilizing OpenAI-compatible endpoints under the hood)
model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.1
)

# The active Go server endpoint
GO_API_URL = "http://localhost:8080/api/allocate"

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

# Instantiate our custom CodeAgent
agent = CodeAgent(
    tools=[check_and_execute_go_allocation],
    model=model
)

def run_interactive_hitl_scheduling(task: str):
    """Executes a Human-in-the-Loop plan customization cycle.
    
    This pattern intercepts the LLM's raw intent, forces a structural planning phase,
    prompts the human operator for edits, and then runs the corrected plan safely.
    """
    print("\n" + "="*80)
    print("[HITL ORCHESTRATION ENGINE INITIALIZED]")
    print(f"Goal: {task}")
    print("="*80)
    
    # Step 1: Force the LLM to generate a chronological step-by-step action plan
    planning_prompt = (
        f"You are an expert scheduler. Analyze this task: '{task}'. "
        "Draft a structured, chronological list of actions to complete this task. "
        "Format your response strictly as a numbered list of steps (e.g., '1. Action A', '2. Action B'). "
        "Do not run any tools yet. Simply output the plan."
    )
    
    print("\n[HITL Phase 1] Querying LLM planner to formulate initial execution steps...")
    initial_plan = model.generate([{"role": "user", "content": planning_prompt}])
    
    # Securely extract raw string content from ChatMessage object to prevent strip AttributeErrors
    plan_text = initial_plan.content if hasattr(initial_plan, "content") else str(initial_plan)
    
    print("\n" + "-"*50)
    print("🔍 PROPOSED AUTOMATED SCHEDULING PLAN:")
    print("-" * 50)
    print(plan_text.strip())
    print("-" * 50)
    
    # Step 2: Prompt the Human Operator for plan customization / approval
    print("\n💡 HUMAN-IN-THE-LOOP INTERCEPT POINT:")
    print("You can approve this plan, modify steps, or force alternative resource allocations (e.g., 'Change Room to R101').")
    
    user_feedback = input("\nEnter feedback/approval (Leave empty to approve as-is): ").strip()
    
    if not user_feedback:
        print("\n✅ Plan approved by Human Operator. Executing baseline plan...")
        execution_prompt = (
            f"Execute the following approved plan: \n{plan_text}\n\n"
            "Use your tools to carry out the operations. Complete the task."
        )
    else:
        print(f"\n⚙️ Merging custom human constraints: '{user_feedback}'")
        execution_prompt = (
            f"You must complete this task: '{task}'. "
            f"The human supervisor has adjusted your initial plan with this feedback: '{user_feedback}'. "
            "Formulate a corrected strategy integrating this feedback, and use your tools to execute it."
        )
        
    print("\n[HITL Phase 2] Dispatched to agent execution pipeline...")
    agent.run(execution_prompt)
    print("\n" + "="*80)

if __name__ == "__main__":
    # Test task designed to evaluate room allocation fallbacks and trigger HITL overrides
    sample_task = (
        "Schedule the PHY101 exam in Room R102 with Prof. Sarah (FAC01) for Monday Forenoon (MON_FN). "
        "If R102 has a conflict, plan a fallback allocation."
    )
    
    # Check if the Go backend is online before starting
    try:
        requests.get("http://localhost:8080/api/allocate", timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n[WARNING] Go Backend Server appears to be offline at localhost:8080!")
        print("Please run: 'go run backend/main.go' in another terminal window first.")
        print("Starting HITL simulation anyway...\n")
        
    run_interactive_hitl_scheduling(sample_task)