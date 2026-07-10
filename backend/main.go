package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// AllocationRequest defines the incoming JSON payload from our Python Agent
type AllocationRequest struct {
	ExamCode    string `json:"exam_code"`
	RoomCode    string `json:"room_code"`
	TimeslotID  string `json:"timeslot_id"`
	ProfessorID string `json:"professor_id"`
}

// AllocationResponse defines the outgoing JSON confirmation
type AllocationResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
}

// SchedulerEngine holds our state and our concurrency locks
type SchedulerEngine struct {
	mu           sync.Mutex
	bookedRooms  map[string]bool // Maps "RoomCode_TimeslotID" to true if booked
	bookedProcs  map[string]bool // Maps "ProfessorID_TimeslotID" to true if booked
}

// NewSchedulerEngine initializes the engine
func NewSchedulerEngine() *SchedulerEngine {
	return &SchedulerEngine{
		bookedRooms: make(map[string]bool),
		bookedProcs: make(map[string]bool),
	}
}

// HandleBooking is the concurrent HTTP handler for allocation requests
func (s *SchedulerEngine) HandleBooking(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req AllocationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	roomKey := fmt.Sprintf("%s_%s", req.RoomCode, req.TimeslotID)
	procKey := fmt.Sprintf("%s_%s", req.ProfessorID, req.TimeslotID)

	// --- CRITICAL SECTION BEGIN ---
	// We lock the thread. If 1,000 requests hit this at the exact same millisecond,
	// Go will process them safely one by one, preventing any double-booking race conditions.
	s.mu.Lock()
	
	// Simulate database processing latency
	time.Sleep(50 * time.Millisecond)

	if s.bookedRooms[roomKey] {
		s.mu.Unlock() // Unlock before returning!
		sendResponse(w, http.StatusConflict, "Conflict", fmt.Sprintf("Room %s is already booked for %s", req.RoomCode, req.TimeslotID))
		return
	}

	if s.bookedProcs[procKey] {
		s.mu.Unlock() // Unlock before returning!
		sendResponse(w, http.StatusConflict, "Conflict", fmt.Sprintf("Professor %s is already assigned during %s", req.ProfessorID, req.TimeslotID))
		return
	}

	// Commit the allocation to state
	s.bookedRooms[roomKey] = true
	s.bookedProcs[procKey] = true
	
	s.mu.Unlock()
	// --- CRITICAL SECTION END ---

	successMsg := fmt.Sprintf("Successfully scheduled %s in %s with %s for %s", req.ExamCode, req.RoomCode, req.ProfessorID, req.TimeslotID)
	sendResponse(w, http.StatusOK, "Success", successMsg)
}

func sendResponse(w http.ResponseWriter, statusCode int, status, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(AllocationResponse{Status: status, Message: message})
}

func main() {
	engine := NewSchedulerEngine()

	// Register our API route
	http.HandleFunc("/api/allocate", engine.HandleBooking)

	port := ":8080"
	fmt.Printf("[SYSTEM START] Go Scheduling API running on http://localhost%s\n", port)
	fmt.Println("Concurrency protection: ACTIVE (sync.Mutex)")
	
	log.Fatal(http.ListenAndServe(port, nil))
}