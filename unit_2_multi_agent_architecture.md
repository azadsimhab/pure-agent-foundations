Unit 2 Architecture: Hierarchical Multi-Agent Orchestration

As systems scale, injecting every available tool into a single LLM's system prompt leads to Context Window Pollution and severe instruction drift. To build an enterprise-grade Exam Allocation System, we implement the Manager-Worker (Hierarchical) Pattern using smolagents.

1. The Principle of Least Privilege & Tool Isolation

By splitting our cognitive engine into multiple agents, we enforce strict security and performance boundaries:

The Scheduler Agent is strictly isolated. It has zero access to the internet, web scrapers, or third-party APIs. It only understands database constraints, room capacities, and proctor limits.

The Research Agent is sandboxed. It can scrape the web and fetch currency rates, but it has zero authorization to mutate the university scheduling tables.

2. The Orchestrator (Manager Agent)

The Manager Agent acts as the system's API gateway. It does not possess any tools of its own, except for the ability to delegate tasks to its workers.

When a University Admin submits a complex prompt:

"Find the current USD to INR exchange rate to calculate visiting professor stipends, and then schedule the PHY101 exam in Room R102 for Monday Forenoon."

The Manager executes a deterministic ReAct loop:

Thought: I need to fetch the exchange rate, and I need to schedule an exam. I will use the research_agent first.

Action: research_agent(task="Get USD to INR rate")

Observation: 1 USD = 83.50 INR.

Thought: Now I will use the scheduler_agent to book the room.

Action: scheduler_agent(task="Schedule PHY101 in R102 for MON_FN")

Observation: Allocation successful.

3. The code_vs_json_actions Verification

As illustrated in our theoretical research, we exclusively utilize CodeAgents for both our Manager and Worker nodes. If the Manager needs to iterate through a list of 5 different exams to schedule, it writes a Python for loop to pass them sequentially to the scheduler_agent, rather than executing 5 separate JSON API roundtrips. This guarantees $O(1)$ network execution scaling on the orchestration layer.