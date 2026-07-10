Blueprint: Intelligent Exam Seating & Invigilator Allocation System

This document outlines the master architecture, development roadmap, and multi-framework integration plan for our flagship portfolio project.

1. Unified Multi-Tier System Architecture

Instead of a basic CRUD application, we are building a decoupled, multi-framework enterprise stack where high-speed concurrency, stateful workflows, and context-augmented intelligence are layered purposefully:

┌────────────────────────────────────────────────────────┐
│             1. CLIENT INTERFACE (Flutter)              │
│  - Interactive Admin Scheduling grid.                  │
│  - Natural language conversational assistant sheet.     │
└───────────────────────────┬────────────────────────────┘
                            │ (JSON-RPC)
                            ▼
┌────────────────────────────────────────────────────────┐
│           2. COGNITIVE WORKFLOWS (LangGraph)           │
│  - Directed Acyclic Graph (DAG) managing conversation.  │
│  - Transitions state from:                             │
│    [Gather] ──► [Retrieve] ──► [Evaluate] ──► [Book]    │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐┌───────────────────────────┐
│  3. CONTEXT (LlamaIndex)  ││   4. CODE ENGINE (smol)   │
│ - Indexes university PDFs ││ - Runs CodeAgents locally│
│ - Semantic search over    ││ - Compiles multi-step     │
│   scheduling guidelines.  ││   Python routines $O(1)$. │
└─────────────┬─────────────┘└────────────┬──────────────┘
              │                           │
              └─────────────┬─────────────┘
                            │ (Secure HTTP REST API)
                            ▼
┌────────────────────────────────────────────────────────┐
│             5. TRANSACTIONS & CORE (Go API)            │
│  - High-performance scheduling API written in Go.      │
│  - Thread-safe memory allocation using `sync.Mutex`.   │
│  - Pessimistic Row Locking (`SELECT ... FOR UPDATE`).  │
└───────────────────────────┬────────────────────────────┘
                            │ (Raw SQL Transactions)
                            ▼
┌────────────────────────────────────────────────────────┐
│              6. PERSISTENCE LAYER (MySQL)              │
│  - Normalized relational database schema.              │
└────────────────────────────────────────────────────────┘


2. Decoupled Framework Responsibilities

Go Backend: Serves as the ultimate mathematical source of truth. Under concurrent scheduling loads, its memory-level lock guarantees that two parallel agent requests cannot double-book a classroom or over-allocate an invigilator.

LangGraph: Manages the orchestration flow. Rather than letting an LLM loop indefinitely without guidance, LangGraph acts as a finite state machine, forcing the agent to structurally complete requirements gathering before executing operations.

LlamaIndex: Parses and vectorizes the institutional rulebook (PDF format). It checks semantic constraints (such as "invigilators must have at least an 8-hour break between sessions") that are too soft or complex to hardcode into relational SQL constraints.

smolagents: Executes dynamic, high-speed Python loops locally inside sandboxed runtimes to process variables instantly without quadratic network roundtrips.

3. High-Performance Concurrency Guard (Go implementation)

To secure our data target under high concurrency, our Go API encapsulates allocations within locked synchronization wrappers:

s.mu.Lock()
defer s.mu.Unlock()

if s.bookedRooms[roomKey] {
    // Gracefully reject the duplicate request instantly
    return
}


This isolates the transaction instantly. Even if the orchestrating agent is compromised or attempts multiple rapid checks, the Go layer ensures absolute transaction safety.