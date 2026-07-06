Deep Dive: The Architectural Shift from JSON Tool-Calling to Code Agents

In modern agentic systems design, choosing your execution paradigm dictates your system's latency, token consumption patterns, and runtime reliability. This document analyzes the computer science and mathematical trade-offs between JSON-based Tool-Calling (implemented in agent.py) and Code Agents (implemented in smol_agent.py) using our institutional Exam Seating & Invigilator Allocation System as a target case study.

It is heavily informed by the core lessons of the Hugging Face AI Agents Course, specifically referencing the CodeAct (Code as Action) and ReAct Prompting paradigms.

1. Prompting Paradigms: From CoT to ReAct

To understand how an agent acts, we must look at how it thinks. As illustrated in the course literature (specifically referencing the classic comparisons in ReAct.png), raw models struggle with complex, multi-step logical operations when forced to generate answers directly.

(a) Zero-shot Prompting:
User ──> [LLM] ──> "The answer is 8" (Incorrect Hallucination due to lack of working memory)

(b) Zero-shot Chain-of-Thought (CoT) [ReAct.png (d)]:
User ──> [LLM] ──> "Let's think step by step. 16/2 = 8. 8/2 = 4." ──> "The answer is 4" (Correct)


While Chain-of-Thought (CoT) introduces a silent internal reasoning space, it cannot interact with the outside world. The ReAct Paradigm merges this step-by-step reasoning with concrete tool-execution loops:

$$\text{Thought} \longrightarrow \text{Action} \longrightarrow \text{Observation} \longrightarrow \text{Updated Thought}$$

In our scheduling system, this prevents the LLM from hallucinating room bookings, forcing it to dynamically cross-reference its planning states against database constraints.

2. The Context Window Pollution Bottleneck ($O(N)$ Token Growth)

In a traditional JSON agent (like our agent.py implementation), every step of the reasoning loop requires a complete API network roundtrip. Because language models are mathematically stateless, the complete history of previous thoughts, JSON action commands, and string observations must be continuously concatenated and fed back into the model's active attention window on every turn.

We can represent this sequence state $M$ over time step $t$ as:

$$M_{t+1} = M_t \cup \{Thought_t, Action_t, Observation_t\}$$

As the number of scheduling evaluation loops $t$ increases to satisfy complex scheduling constraints, the number of tokens inside the context window grows linearly:

$$\text{Tokens}_{total} = O(t)$$

The Cost Implications:

Quadratic Attention Latency: Self-attention calculations scale quadratically with sequence length ($O(L^2)$). As the loop runs, every subsequent step becomes slower and more expensive.

Context Fragmentation: Long histories of legacy raw text database strings distract the model's positional attention, leading to scheduling hallucinations or parameter errors.

3. Code-Execution Agents: Constant Complexity $O(1)$

As shown in the course comparison code-vs-json-actions.png, Code Agents (the CodeAct paradigm) resolve this bottleneck by changing the compiler target. Instead of instructing the LLM to output a static JSON command for a single tool step, the LLM compiles and executes a complete Python program locally.

Instead of running $N$ network loops to check $N$ different variables, the LLM writes a Python loop that runs in milliseconds inside a sandboxed interpreter, returning only the final parsed result.

              ┌─────────────────────────────────────────────────────────┐
              │           THE CODEACT COMPLEXITY COMPARISON             │
              └─────────────────────────────────────────────────────────┘

  [JSON Paradigm (Multi-Turn) - Left of code-vs-json-actions.png]
  LLM ──(check R101)──> Database ──(unoccupied)───> LLM ──(check FAC01)──> Database ... [O(N) Turns]

  [CodeAct Paradigm (Single-Turn) - Right of code-vs-json-actions.png]
  LLM ──(Generates entire Python loop over list)───> Local Interpreter ────> [O(1) Turn]


Side-by-Side Execution Sequence (Exam Seating Comparison)

Suppose we need to check if Room R102 is available during MON_FN. If unavailable, we must loop through fallback rooms (R101, LH201) to find a room with sufficient capacity for 45 students.

A. The JSON Agent Protocol (6+ Network Turns):

Turn 1 (LLM -> Client): {"action": "check_room_availability", "room": "R102", "slot": "MON_FN"}

Turn 1 (Client -> LLM): Observation: Conflict: Room R102 booked.

Turn 2 (LLM -> Client): {"action": "check_room_availability", "room": "R101", "slot": "MON_FN"}

Turn 2 (Client -> LLM): Observation: Available. Seating Capacity: 30.

Turn 3 (LLM -> Client): Thinks: "Wait, the student count is 45, but R101 only holds 30. Too small." Output: {"action": "check_room_availability", "room": "LH201", "slot": "MON_FN"}

Turn 3 (Client -> LLM): Observation: Available. Seating Capacity: 120.

Turn 4 (LLM -> Client): Output: FINAL_ANSWER: Scheduled in LH201.

B. The Code Agent Protocol (1 Network Turn - Matches Right of code-vs-json-actions.png):

Turn 1 (LLM -> Client): Generates and runs this structured Python script locally:

candidate_rooms = ["R102", "R101", "LH201"]
target_exam_students = 45
assigned_room = None

for room in candidate_rooms:
    status = check_room_availability(room, "MON_FN")
    if "Available" in status:
        # Extract capacity from status string or context
        capacity = 120 if room == "LH201" else (30 if room == "R101" else 0)
        if capacity >= target_exam_students:
            assigned_room = room
            break

if assigned_room:
    print(f"Success: Selected room {assigned_room}")
else:
    print("Failed to find a viable classroom.")


Turn 1 (Client -> LLM): The local interpreter executes the script in milliseconds and returns the printed result: "Success: Selected room LH201"

LLM Output: FINAL_ANSWER: Scheduled in LH201.

4. Structural Comparison Matrix

Architectural Feature

JSON Tool-Calling (agent.py)

Code-Execution Agents (smol_agent.py)

Output Target

Static, structured JSON strings

Dynamic, executable Python scripts

Execution Environment

Client-side application parser

Isolated, sandboxed local Python interpreter

Network Roundtrips

High ($O(N)$ network loops)

Low (Consolidates steps into $O(1)$ request)

Algorithmic Expressiveness

Rigid (Cannot run loops, variables, or branches)

Unlimited (Supports local variables, standard loops)

Schema Generation Dependency

Brittle (Requires strict JSON parser formats)

Robust (Uses Python type hints & functional docstrings)

Security Risk Profile

Low (Only pre-written code can run)

High (Requires sandbox limits to prevent execution abuse)

5. Key Engineering Takeaways

Stop and Parse is Mandatory: No matter the format, the LLM must halt token generation immediately after outputting its command blocks (json or python). This transfers thread execution control back to your Go/Python orchestration layer.

The Docstring is a Runtime Dependency: When using @tool in code-execution frameworks, Python's dynamic reflection parses your code comments and annotations directly into the LLM's system prompt. A missing docstring or incorrect parameter type hint doesn't just cause a linter warning—it completely breaks the agent's tool alignment at runtime.