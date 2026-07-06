import os
import sys
import json
from google import genai
from google.genai import types

# Hardcoded state table simulating our SQL Database tables
MOCK_DATABASE = {
    "rooms": {
        "R101": {"capacity": 60, "status": "Available"},
        "R102": {"capacity": 30, "status": "Booked (Exam CS102, MON_FN)"}
    }
}

def check_room_availability(room_code: str) -> str:
    """Deterministic read tool for room capacity and current bookings."""
    code = room_code.strip().upper()
    if code not in MOCK_DATABASE["rooms"]:
        return f"Error: Room {code} is not registered."
    room = MOCK_DATABASE["rooms"][code]
    return f"Room {code} status: {room['status']}, seating capacity: {room['capacity']} students."

# Mapping string actions to executable python functions
TOOL_MAP = {
    "check_room_availability": check_room_availability
}

class PureAgent:
    def __init__(self):
        # Initialize raw Gemini Client (automatically reads GEMINI_API_KEY env)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[Fatal Error] GEMINI_API_KEY is not defined in the environment.")
            sys.exit(1)
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.5-flash'
        
        # Inject structural instructions: Defining how the model MUST format actions
        self.system_instruction = (
            "You are an institutional scheduling orchestrator. You operate strictly inside a "
            "Thought -> Action -> Observation loop.\n\n"
            "Available tools:\n"
            "- check_room_availability(room_code: str): Returns capacity and current booking status.\n\n"
            "To call a tool, you must generate a JSON codeblock containing 'action' "
            "and 'action_input', and STOP generating immediately. Example:\n"
            "```json\n"
            '{"action": "check_room_availability", "action_input": "R102"}\n'
            "```\n\n"
            "Once you receive an Observation, write your next Thought.\n"
            "When the objective is completed, output your final result starting with 'FINAL_ANSWER: '."
        )
        self.memory = []

    def run(self, user_task: str, max_steps: int = 5):
        print(f"[Initialization] Starting Task: {user_task}")
        print("-" * 70)
        
        # New Google GenAI SDK requires strict types.Content objects
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
                # Send the complete state history to the stateless API
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=self.memory,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.1
                    )
                )
            except Exception as e:
                print(f"[API Error] Generation failed: {e}")
                return

            llm_output = response.text
            print(f"[Agent Thought/Output]:\n{llm_output}")
            
            # 1. Check Exit Condition
            if "FINAL_ANSWER:" in llm_output:
                print("\n[Success] Final Answer reached. Terminating ReAct cycle.")
                break
                
            # 2. Stop and Parse Step: Intercept markdown JSON codeblocks
            if "```json" in llm_output:
                try:
                    # Isolate the JSON string
                    json_str = llm_output.split("```json")[1].split("```")[0].strip()
                    tool_call = json.loads(json_str)
                    
                    action_name = tool_call["action"]
                    action_input = tool_call["action_input"]
                    
                    # 3. Deterministic Local Execution (Observation)
                    if action_name in TOOL_MAP:
                        print(f"[Executing Tool Call]: {action_name}('{action_input}')")
                        observation = TOOL_MAP[action_name](action_input)
                        print(f"[Observation Received]: {observation}")
                        
                        # Append historical steps using the required SDK objects to preserve attention state
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
                    # Graceful Error recovery fed back into the loop
                    error_msg = f"Parser Error: Your tool call failed. Details: {str(e)}. Correct your JSON formatting."
                    print(f"[{error_msg}]")
                    self.memory.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=llm_output)]
                        )
                    )
                    self.memory.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=error_msg)]
                        )
                    )
            else:
                # If LLM just chatted without calling a tool or outputting final answer
                fallback_msg = "System Warning: You did not execute a tool or output a FINAL_ANSWER. Use a valid JSON block."
                print(f"[{fallback_msg}]")
                self.memory.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=llm_output)]
                    )
                )
                self.memory.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=fallback_msg)]
                    )
                )

if __name__ == "__main__":
    agent = PureAgent()
    # Forces the agent to evaluate room constraints using its internal ReAct flow
    agent.run("Can we schedule the PHY101 exam in Room R102 on Monday forenoon (MON_FN)?")