import os
import sys

try:
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
    from llama_index.llms.gemini import Gemini
    from llama_index.embeddings.gemini import GeminiEmbedding
except ImportError:
    print("\n[Dependency Notice] Installing LlamaIndex Core and Gemini connectors...")
    os.system("pip install llama-index llama-index-llms-gemini llama-index-embeddings-gemini")
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
    from llama_index.llms.gemini import Gemini
    from llama_index.embeddings.gemini import GeminiEmbedding

# --- API KEY SECURITY GUARD ---
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    print("\n[CRITICAL ERROR] GEMINI_API_KEY is missing from your environment variables!")
    print("Please run: $env:GEMINI_API_KEY='your_key_here' in your terminal.")
    sys.exit(1)

# We use Google's lightning-fast gemini-2.5-flash model for policy analysis
Settings.llm = Gemini(
    model_name="models/gemini-2.5-flash",
    api_key=gemini_key,
    temperature=0.1
)

# Crucial Architectural Change: We use 'models/gemini-embedding-001' to prevent the v1beta 404 API error
Settings.embed_model = GeminiEmbedding(
    model_name="models/gemini-embedding-001",
    api_key=gemini_key
)

def evaluate_schedule_policy(query_prompt: str) -> str:
    """Queries the indexed institutional rulebook using vector semantic search to validate scheduling requests.
    
    Args:
        query_prompt: The scheduling query or plan to check for policy violations.
    """
    try:
        # Check if the policy document exists locally
        if not os.path.exists("university_policy_manual.txt"):
            return "Policy Database Offline: File university_policy_manual.txt was not found."
            
        # Parse and ingest the raw text manual
        reader = SimpleDirectoryReader(input_files=["university_policy_manual.txt"])
        documents = reader.load_data()
        
        # Build the vector index in memory and convert documents to vectors
        index = VectorStoreIndex.from_documents(documents)
        
        # Build the semantic query engine
        query_engine = index.as_query_engine(similarity_top_k=2)
        
        system_context_query = (
            f"Context: Analyze the following scheduling request against Krea University's strict policies. "
            f"If there is any conflict or violation (such as visiting faculty timeslot violations, consecutive room "
            f"lounging limits, or capacity limits), explain the violation in detail. "
            f"Request to evaluate: {query_prompt}"
        )
        
        response = query_engine.query(system_context_query)
        return str(response)
        
    except Exception as e:
        return f"Policy Evaluation Failed. Exception Details: {str(e)}"

if __name__ == "__main__":
    # Test cases to prove semantic query capability
    test_1 = "Can we schedule visiting professor Prof. Sarah (FAC01) for an exam during MON_AN (Monday Afternoon)?"
    test_2 = "Can we schedule an exam with 85 students in Room R101?"
    
    print("\n[LLAMAINDEX SYSTEM INITIALIZATION] Running semantic policy checks...")
    print("-" * 75)
    print(f"Query: {test_1}")
    print(f"Response: {evaluate_schedule_policy(test_1)}")
    print("-" * 75)
    print(f"Query: {test_2}")
    print(f"Response: {evaluate_schedule_policy(test_2)}")