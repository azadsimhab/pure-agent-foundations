# Theoretical Deep Dive: Stop Sequences and Hallucination Mitigation

In the foundational **Thought-Action-Observation** loop, a failure to programmatically halt the model's token prediction immediately after it formats an action results in the collapse of the state machine.

This document explores the mathematics of autoregressive token prediction and explains why **Stop Sequences** are a mandatory runtime guardrail for our **Exam Seating & Invigilator Allocation System**.

---

## 1. The Mathematics of Autoregressive Generation

A Large Language Model is a probabilistic sequence generator. Given a historical sequence of tokens $S = \{w_1, w_2, \dots, w_k\}$, the model computes the probability distribution of the next token $w_{k+1}$:

$$P(w_{k+1} \mid w_1, w_2, \dots, w_k)$$

When the model is running inside an agent loop, we prompt it to output a tool command in JSON or Python code:

```text
Thought: I need to verify if Room R101 is available.
Action: {"action": "check_room_availability", "room_code": "R101"}
```

If the orchestration engine does not intervene, the model will proceed to predict $w_{k+3}, w_{k+4}, \dots$ using its own weights. Since the string `"Observation:"` frequently follows an `"Action:"` block in its training data, the model's highest probability output is:

```text
Observation: Room R101 is available. Seating Capacity: 60 students.
Thought: I now know the final answer.
Final Answer: I have scheduled the exam in Room R101.
```

### The Architectural Failure (State Corruption)
The LLM has **hallucinated** the state of the database. It did not make an API request to our Go backend, and it did not verify the actual room capacity in MySQL. The model predicted the most "plausible-sounding" response, corrupting the execution loop.

---

## 2. Decoupling Logic with Stop Sequences

To prevent this state corruption, we must enforce a strict division of labor between the probabilistic planner (the LLM) and the deterministic execution engine (our Python/Go tools).

```text
   [LLM: Probabilistic Planner]           [Orchestrator]             [Go/MySQL Backend]
                 │                               │                           │
  1. Generates: "Thought + Action"               │                           │
  2. Encounters Stop Sequence ("Observation:") ──►                           │
  3. [HALT GENERATION]                           │                           │
                 │                     4. Parses tool arguments              │
                 │                     5. Dispatches API call ───────────────►
                 │                               │              6. Executes transaction
                 │                               │              7. Returns real DB state
                 │                     8. Appends true Observation           ◄───────┘
                 │                               │
  9. [RESUME GENERATION] ◄───────────────────────┘
```

By supplying a `stop_sequences` parameter to the generation config, the orchestrator instructs the inference engine to monitor token emissions. The moment the model outputs a token sequence matching `"Observation:"`, generation halts immediately, transferring thread control back to our application layer.

---

## 3. Why This Protects the Go & MySQL Core

In our hybrid architecture, your Go backend uses **pessimistic row locking** to keep room allocations thread-safe. If an agent could hallucinate database states:

* Two different user sessions could attempt to book Room R101 at the same time.
* If session A's agent hallucinations state checks, it might bypass the Go booking endpoint entirely, leading to double-bookings or database state inconsistencies.

By implementing strict stop-token boundaries, the agent is forced to step down and make a legitimate, synchronous network request to the Go backend API before it is allowed to continue thinking.
