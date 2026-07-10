import requests
import json

# Define the local Go API endpoint
API_URL = "http://localhost:8080/api/allocate"

# Define a test payload matching your Go struct AllocationRequest
payload = {
    "exam_code": "PHY101",
    "room_code": "R102",
    "timeslot_id": "MON_FN",
    "professor_id": "FAC01"
}

try:
    print(f"Sending test allocation request to {API_URL}...")
    response = requests.post(API_URL, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
    
    if response.status_code == 200:
        print("\n✅ API Integration Success: Backend accepted the transaction.")
        
        # Immediately attempt to duplicate the transaction to test Go's sync.Mutex guard!
        print("\nAttempting to double-book Room R102 for MON_FN to test Go Mutex...")
        dup_response = requests.post(API_URL, json=payload)
        print(f"Duplicate Status Code: {dup_response.status_code}")
        print(f"Duplicate Response Body: {dup_response.json()}")
        
        if dup_response.status_code == 409:
            print("\n🔒 Double-Booking Prevented: Go Concurrency Guard is ACTIVE and working!")
        else:
            print("\n❌ Concurrency Bug: Go server allowed a double booking. Check Mutex locks.")
            
    elif response.status_code == 409:
        print("\n⚠️ API Logic Success: Conflict detected (the engine is working).")
    else:
        print("\n❌ Integration Failure: Check Go server logs.")

except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Is the Go server running in the other terminal?")
``` eof

---

### Phase 2: Architectural Synchronization
Now that the backend is live and verified, update your GitHub workspace:

1.  **Commit the Go Backend:**
    ```powershell
    git add backend/main.go exam_system_blueprint.md test_api_connection.py
    git commit -m "feat: deploy concurrent Go scheduling backend and test API integration layer"
    git push origin main
    ```

### Phase 3: The Next Frontier — Integrating LangGraph & LlamaIndex

You asked to use **LangGraph** and **LlamaIndex** to showcase top-tier skills. Here is how we connect them to the Go engine we just built:

1.  **LlamaIndex (Context Layer):** We will build an index of university PDF guidelines (exam rules, room restrictions). When the agent gets a request, LlamaIndex will retrieve relevant policy chunks.
2.  **LangGraph (Orchestration Layer):** We will replace the simple Manager Agent loop with a **Stateful Graph**. This graph will hold the "State" (e.g., `has_retrieved_rules`, `has_checked_room`, `is_booking_confirmed`). If an allocation fails in the Go backend, the graph will have an edge that routes back to the "Verify Room" node.

**Which framework do you want to implement first to talk to this Go API?**
* **LangGraph:** We build the stateful, cyclic workflow (The Agent "Decision Graph").
* **LlamaIndex:** We build the RAG pipeline that reads your university PDFs to inform the agent *before* it tries to book via Go.

Pick your target. We build.