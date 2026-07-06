import os
import sys
import json
from google import genai
from google.genai import types

# Mock legacy database representation
MOCK_EXAMS = {
    "PHY101": {"course_name": "Engineering Physics", "student_count": 25}
}
MOCK_ROOMS = {
    "R102": {"capacity": 30, "status": "Booked (Exam CS102, MON_FN)"},
    "R101": {"capacity": 60, "status": "Available"}
}

def verify_room(room_code: str) -> str:
    """Mock database reader mimicking our safe SQL adapter."""
    code = room_code.strip().upper()
    if code not in MOCK_ROOMS:
        return f"Error: Room {code} is not registered."
    room = MOCK_ROOMS[code]
    return f"DB_STATUS: Room {code} status is {room['status']}, capacity is {room['capacity']}."

TOOL_MAP = {
    "verify_room": verify_room
}

class StopSequenceAgent:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[Fatal Error] GEMINI_API_KEY is not defined in the environment.")
            sys.exit(1)
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.5-flash'
        
        # Defining the system instructions and explicit stop formatting rules
        self.system_instruction = (
            "You are an institutional scheduling agent. You operate inside a "
            "Thought -> Action -> Observation loop.\n\n"
            "Available tools:\n"
            "- verify_room(room_code: str): Queries the physical status and capacity of an exam hall.\n\n"
            "To call a tool, generate a JSON codeblock containing 'action' and 'action_input', "
            "append 'Observation:' on the next line, and STOP generation. Example:\n"
            "```json\n"
            '{"action": "verify_room", "action_input": "R102"}\n'
            "```\n"
            "Observation:\n\n"
            "Do not hallucinate or write anything after the 'Observation:' tag. Let the environment respond.\n"
            "When the final allocation is resolved, respond starting with 'FINAL_ANSWER: '."
        )
        self.memory = []

    def run(self, user_task: str, max_steps: int = 5):
        print(f"[Initialization] Starting Task: {user_task}")
        print("-" * 75)
        
        self.memory.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_task)]
            )
        )
        
        step = 0
        while step < max_steps:
            step += 1
            print(f"\n--- STEP {step} ---")
            
            try:
                # We pass 'stop_sequences' inside the configuration.
                # This instructs the Gemini model to freeze execution instantly when 'Observation:' is generated.
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=self.memory,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.1,
                        stop_sequences=["Observation:", "Observation:\n"]
                    )
                )
            except Exception as e:
                print(f"[API Error] Generation failed: {e}")
                return

            llm_output = response.text
            print(f"[Agent Thought/Output]:\n{llm_output}")
            
            # Check if final answer has been computed
            if "FINAL_ANSWER:" in llm_output:
                print("\n[Success] Execution complete. Terminating Agent loop.")
                break
                
            # Intercept and Parse
            if "```json" in llm_output:
                try:
                    json_str = llm_output.split("```json")[1].split("```")[0].strip()
                    tool_call = json.loads(json_str)
                    
                    action_name = tool_call["action"]
                    action_input = tool_call["action_input"]
                    
                    if action_name in TOOL_MAP:
                        print(f"\n[System Alert]: Generation was halted cleanly by stop sequence.")
                        print(f"[Orchestrator Execution]: Dispatching query to local mock database...")
                        
                        # Real execution of our database tool
                        observation = TOOL_MAP[action_name](action_input)
                        print(f"[True Observation Received]: {observation}")
                        
                        # Pack historical turn and feed true database state into conversational context
                        self.memory.append(
                            types.Content(
                                role="model",
                                parts=[types.Part.from_text(text=llm_output)]
                            )
                        )
                        self.memory.append(
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=f"Observation: {observation}")]
                            )
                        )
                    else:
                        raise ValueError(f"Tool '{action_name}' is not registered.")
                except Exception as e:
                    error_msg = f"Parser Error: Your tool call failed. Details: {str(e)}."
                    print(f"[{error_msg}]")
                    self.memory.append(types.Content(role="model", parts=[types.Part.from_text(text=llm_output)]))
                    self.memory.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))
            else:
                fallback_msg = "System Warning: Use a valid JSON block containing your action."
                self.memory.append(types.Content(role="model", parts=[types.Part.from_text(text=llm_output)]))
                self.memory.append(types.Content(role="user", parts=[types.Part.from_text(text=fallback_msg)]))

if __name__ == "__main__":
    agent = StopSequenceAgent()
    agent.run("Determine if we can schedule PHY101 in Room R102 on Monday forenoon.")