import os
import json
from google import genai
from google.genai import types

# 1. Define the deterministic tool (The 'Outside World' action)
def get_property_tax(location: str) -> str:
    """Calculates property tax rates for a given location."""
    loc = location.lower()
    if "new york" in loc:
        return "Property tax rate is 1.62%"
    elif "california" in loc:
        return "Property tax rate is 0.75%"
    else:
        return "Standard regional property tax rate is 1.1%"

# Map string names to the actual executable Python functions
TOOL_MAP = {
    "get_property_tax": get_property_tax
}

class PureAgent:
    def __init__(self):
        # Initialize the client (automatically reads GEMINI_API_KEY env)
        self.client = genai.Client()
        self.model_id = 'gemini-2.5-flash'
        
        # 2. Set ReAct system instructions
        self.system_instruction = (
            "You are a multi-step execution agent. You solve tasks by looping through: "
            "Thought -> Action -> Observation.\n\n"
            "Available tools:\n"
            "- get_property_tax(location: str): Returns tax details for a city or state.\n\n"
            "To call a tool, you must output a valid JSON block inside markdown brackets, "
            "and STOP generating further text. Example:\n"
            "```json\n"
            '{"action": "get_property_tax", "action_input": "New York"}\n'
            "```\n\n"
            "When you have the final answer based on observations, respond with 'FINAL_ANSWER: <your answer>'"
        )
        self.memory = []

    def run(self, user_task: str, max_steps: int = 5):
        print(f"[Initialization] Task: {user_task}")
        print("-" * 60)
        
        # The new SDK requires strict types.Content objects instead of raw dictionaries
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
                # Execute API call with strict history structures
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
            print(f"[Agent Output]:\n{llm_output}")
            
            if "FINAL_ANSWER:" in llm_output:
                print("\n[Success] Final objective achieved.")
                break
                
            # 3. Parse tool block from markdown code fences
            if "```json" in llm_output:
                try:
                    json_str = llm_output.split("```json")[1].split("```")[0].strip()
                    tool_call = json.loads(json_str)
                    
                    action_name = tool_call["action"]
                    action_input = tool_call["action_input"]
                    
                    if action_name in TOOL_MAP:
                        # 4. Execute observation
                        print(f"[Executing Tool]: {action_name}({action_input})")
                        observation = TOOL_MAP[action_name](action_input)
                        print(f"[Observation]: {observation}")
                        
                        # Correctly append historical steps using the required SDK objects
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
                    error_msg = f"Parser Error: {str(e)}. Correct your formatting."
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
                self.memory.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=llm_output)]
                    )
                )
                self.memory.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text="System Reminder: Call a tool using JSON or output FINAL_ANSWER.")]
                    )
                )

if __name__ == "__main__":
    agent = PureAgent()
    agent.run("Compare the property tax implications between living in California and New York.")