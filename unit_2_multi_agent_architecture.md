🎓 Unit 2: Hierarchical Multi-Agent OrchestrationAs AI applications scale, injecting every available system tool into a single LLM's system prompt leads to severe Context Window Pollution, prompt drift, and a high rate of tool hallucinations.To resolve this, our Exam Seating & Invigilator Allocation System implements the Manager-Worker (Hierarchical) Pattern using Hugging Face's smolagents framework.🛠️ 1. The Principle of Least Privilege & Tool IsolationBy splitting our cognitive architecture into multiple specialized agents, we enforce strict security, attention boundaries, and functional isolation:The Academic Scheduler Agent: This agent is strictly isolated. It has zero access to the internet, web scrapers, or external APIs. It possesses exclusive tools to read database records, verify capacities, check invigilator duty limits, and commit row-level allocations.The Web Research Agent: A sandboxed agent designed strictly for information gathering. It can scrape web pages and fetch live financial metadata, but it has zero authorization to view or mutate our academic scheduling database.🧠 2. The Orchestrator (Manager Agent)The Manager Agent acts as the high-level API gateway. It does not carry individual database or search tools. Instead, it delegates complex operational directives to its workers through custom Explicit Delegation Adapters.                           ┌───────────────────────────┐
                           │   Manager Agent (LLM)     │
                           └─────────────┬─────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [delegate_to_researcher]                    [delegate_to_scheduler]
                   │                                           │
                   ▼                                           ▼
     ┌───────────────────────────┐               ┌───────────────────────────┐
     │   Web Research Worker     │               │    Academic Scheduler     │
     │  - DuckDuckGo Search      │               │   - Database Read/Write   │
     │  - Scraper / Text Filters │               │   - Conflict Validation   │
     └───────────────────────────┘               └───────────────────────────┘

🚀 3. CodeAct vs. Text/JSON Tool-CallingAs verified in our experimental testing and illustrated in our reference diagrams, we exclusively utilize CodeAgents over traditional JSON tool-calling models.Why this is mathematically superior:The Latency Problem ($O(N)$): A JSON-based agent must perform separate network roundtrips to evaluate multiple tools (e.g., checking 5 fallback rooms requires 5 distinct LLM generation and parsing cycles).The CodeAct Advantage ($O(1)$): A CodeAgent compiles the entire conditional verification structure into a single Python script at runtime and runs it locally inside a secure sandbox. The network overhead is completely eliminated:# The CodeAgent writes and runs this loop in a single turn!
for room in ["R102", "R101"]:
    status = check_room_availability(room, "MON_FN")
    if "Available" in status:
        execute_exam_allocation("PHY101", room, "FAC01", "MON_FN")
        break
🔒 4. Production Security & GuardrailsTo protect the underlying database from prompt-injection vulnerabilities and runtime crashes, the orchestrator is wrapped in two enterprise-grade layers:Explicit Delegation Wrapper: Prevents structural framework deprecation bugs by manually wrapping sub-agents inside standard Python function decorators.Environment Validation Checks: Explicitly validates the presence of model configuration keys (HF_TOKEN or GEMINI_API_KEY) at execution startup, preventing unhandled deep-framework exceptions.