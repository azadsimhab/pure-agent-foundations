import os
import sys
from typing import List
from smolagents import CodeAgent, Tool, LiteLLMModel

# --- API KEY SECURITY GUARD ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ERROR] GEMINI_API_KEY is missing from your environment variables!")
    print("Please run: $env:GEMINI_API_KEY='your_key_here' in your terminal.")
    sys.exit(1)

# Initialize the Gemini model via LiteLLMModel wrapper
model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.1
)

# --- 1. THE RESTRUCTURING OF KNOWLEDGE ---
# Real-world institutional data parsed into semantic documents
KNOWLEDGE_BASE = [
    {
        "content": "Krea University exam room capacities: Room R101 max limit 30 students, Room R102 max limit 40 students, Room R103 max limit 120 students.",
        "source": "Infrastructure Records Section 1"
    },
    {
        "content": "All university examinations exceeding 50 registered candidates must be assigned to the main hall, Room R103.",
        "source": "Infrastructure Records Section 2"
    },
    {
        "content": "Faculty assignment limits: No invigilator or professor may be scheduled for more than 2 exam slots on a single academic day to prevent fatigue.",
        "source": "Proctoring Guidelines Paragraph 1"
    },
    {
        "content": "Visiting Scholar travel policy: Prof. Sarah (FAC01) is registered as a Visiting Scholar. Visiting scholars are exempt from afternoon scheduling slots (AN) and must only be scheduled for forenoon sessions (FN).",
        "source": "Visiting Faculty Bylaws Clause A"
    },
    {
        "content": "Consecutive slot safety policy: Invigilators cannot be scheduled for consecutive timeslots (e.g., MON_FN followed immediately by MON_AN) unless assigned to Room R101 or R103, which feature adjacent faculty rest lounges. Room R102 has no adjacent lounge and is strictly forbidden for consecutive invigilation.",
        "source": "Proctoring Guidelines Paragraph 2"
    }
]

# --- 2. RESILIENT VECTORLESS COGNITIVE SEMANTIC SEARCH ---
# To prevent environment pipeline dependency breaks during deployment, we implement
# a highly reliable keyword-density semantic weight matching tool.
class AgenticRetrieverTool(Tool):
    name = "policy_retriever"
    description = (
        "Retrieves critical university scheduling guidelines, capacities, and proctoring constraints. "
        "Use this tool to find facts before attempting or confirming any allocation transaction."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": (
                "The search query. This should be an affirmative statement representing the target facts. "
                "For example, instead of 'Can Prof. Sarah work in the afternoon?', query: 'Prof. Sarah visiting scholar afternoon slots'."
            ),
        }
    }
    output_type = "string"

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your query must be a string."
        print(f"\n[RAG Tool] Scanning Knowledge Base for: '{query}'")
        
        # Clean and tokenize the reformulated query
        query_words = set(query.lower().replace("_", " ").split())
        scored_docs = []
        
        for doc in KNOWLEDGE_BASE:
            content_lower = doc["content"].lower()
            # Calculate overlapping term frequency as a primitive semantic score
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored_docs.append((score, doc))
                
        # Sort documents by relevance score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        retrieved = scored_docs[:2]  # Pull top 2 matching documents
        
        if not retrieved:
            return "No matching policy documents found. Try reformulating your search terms with different keywords."
            
        output = "\n===== Retrieved Policy Documents =====\n"
        for idx, (score, doc) in enumerate(retrieved):
            output += f"--- Match {idx + 1} (Score: {score}) [Source: {doc['source']}] ---\n"
            output += f"{doc['content']}\n\n"
        return output

# --- 3. CONSTRUCT THE AGENTIC RAG SYSTEM ---
# Create the retriever tool instance
retriever_tool = AgenticRetrieverTool()

# Build our advanced CodeAgent
agent = CodeAgent(
    tools=[retriever_tool],
    model=model,
    additional_authorized_imports=["time"]
)

if __name__ == "__main__":
    # Test task designed to force query reformulation and self-query correction
    adaptive_task = (
        "Analyze the following administrative plan: 'We want to schedule a large exam with 85 students "
        "in Room R101, and assign visiting professor Prof. Sarah (FAC01) to invigilate a Monday Afternoon "
        "session (MON_AN)'. Use the policy_retriever tool to check if this plan complies with Krea University guidelines. "
        "IMPORTANT: Formulate search queries in affirmative statements (e.g. 'exam room capacities R101' or "
        "'visiting professor Sarah timeslots'). If you detect any guideline violations, state them clearly and "
        "suggest corrected alternatives."
    )
    
    print("\n[AGENTIC RAG SYSTEM INITIALIZATION] Running query reformulation pipeline...")
    print("=" * 80)
    agent.run(adaptive_task)
    print("=" * 80)