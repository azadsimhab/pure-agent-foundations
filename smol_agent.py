import os
import sys
from smolagents import CodeAgent, LiteLLMModel, tool

# =====================================================================
# 1. UNTYPED LEGACY DATABASE INFRASTRUCTURE (Mocking University tables)
# =====================================================================
MOCK_ROOMS = {
    "R101": {"capacity": 60, "building": "Academic Block A"},
    "R102": {"capacity": 30, "building": "Academic Block A"},
    "LH201": {"capacity": 120, "building": "Lecture Hall Complex"}
}

MOCK_EXAMS = {
    "CS102": {"course_name": "Data Structures & Algorithms", "student_count": 45},
    "MAT201": {"course_name": "Linear Algebra", "student_count": 80},
    "PHY101": {"course_name": "Engineering Physics", "student_count": 25}
}

MOCK_INVIGILATORS = {
    "FAC01": {"name": "Prof. Sarah", "max_duties": 3, "current_duties": 1},
    "FAC02": {"name": "Prof. Ratan", "max_duties": 2, "current_duties": 2} # Proctor is at their duty limit!
}

MOCK_ALLOCATIONS = [
    {"room_code": "R102", "timeslot_id": "MON_FN", "faculty_id": "FAC01", "exam_id": "CS102"} # R102 is booked!
]

def raw_legacy_db_query(raw_string_query: str) -> str:
    """Simulates a low-level untyped database read."""
    clean_query = raw_string_query.upper().strip()
    if "R102" in clean_query:
        return "ROOM_FOUND: R102, CAPACITY: 30, STATUS: ACTIVE"
    elif "R101" in clean_query:
        return "ROOM_FOUND: R101, CAPACITY: 60, STATUS: ACTIVE"
    elif "LH201" in clean_query:
        return "ROOM_FOUND: LH201, CAPACITY: 120, STATUS: ACTIVE"
    return "ERROR: ROOM_NOT_FOUND"


# =====================================================================
# 2. UNIT 1 COMPOSABLE TOOLS WITH ADAPTERS & SANITIZATION
# =====================================================================

@tool
def check_room_availability(room_code: str, timeslot_id: str) -> str:
    """
    Checks if a specific exam room is occupied or available for a given timeslot.
    Acts as a secure, typed adapter wrapping the legacy database engine.

    Args:
        room_code: The code representing the room (e.g., 'R101', 'R102', 'LH201').
        timeslot_id: The targeted timeslot ID (e.g., 'MON_FN', 'MON_AN').
    """
    clean_room = room_code.strip().upper()
    clean_slot = timeslot_id.strip().upper()

    # Zero-Trust Input Filter
    forbidden_tokens = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", ";"]
    if any(token in clean_room for token in forbidden_tokens) or any(token in clean_slot for token in forbidden_tokens):
        return "Security Exception: Blocked potential database manipulation attempt."

    raw_status = raw_legacy_db_query(f"SELECT * FROM rooms WHERE code = '{clean_room}'")
    if "ERROR" in raw_status:
        return f"Error: Room '{clean_room}' is not registered in the system database."

    for alloc in MOCK_ALLOCATIONS:
        if alloc["room_code"] == clean_room and alloc["timeslot_id"] == clean_slot:
            return f"Conflict: Room {clean_room} is already booked during timeslot {clean_slot} for Exam {alloc['exam_id']}."

    capacity = MOCK_ROOMS[clean_room]["capacity"]
    return f"Available: Room {clean_room} is unoccupied. Seating Capacity: {capacity} students."


@tool
def check_invigilator_status(faculty_id: str, timeslot_id: str) -> str:
    """
    Evaluates if an invigilator is available, has reached their duty limit, or has a scheduling conflict.

    Args:
        faculty_id: The unique ID of the faculty member (e.g., 'FAC01', 'FAC02').
        timeslot_id: The targeted timeslot ID (e.g., 'MON_FN', 'MON_AN').
    """
    clean_faculty = faculty_id.strip().upper()
    clean_slot = timeslot_id.strip().upper()

    if clean_faculty not in MOCK_INVIGILATORS:
        return f"Error: Faculty ID '{clean_faculty}' is not registered in the system database."

    faculty = MOCK_INVIGILATORS[clean_faculty]

    # Rule 1: Check duty allocation limits
    if faculty["current_duties"] >= faculty["max_duties"]:
        return f"Unavailable: {faculty['name']} ({clean_faculty}) has reached their maximum duties threshold of {faculty['max_duties']}."

    # Rule 2: Check schedule overlap conflicts
    for alloc in MOCK_ALLOCATIONS:
        if alloc["faculty_id"] == clean_faculty and alloc["timeslot_id"] == clean_slot:
            return f"Conflict: {faculty['name']} is already assigned to invigilate in Room {alloc['room_code']} during timeslot {clean_slot}."

    return f"Available: {faculty['name']} has remaining capacity ({faculty['current_duties']}/{faculty['max_duties']} duties assigned)."


@tool
def allocate_exam_schedule(exam_id: str, room_code: str, timeslot_id: str, faculty_id: str) -> str:
    """
    Executes a transaction booking a room and proctor for a specific course exam.

    Args:
        exam_id: The course code of the exam (e.g., 'CS102', 'MAT201', 'PHY101').
        room_code: The code representing the room (e.g., 'R101', 'LH201').
        timeslot_id: The targeted timeslot ID (e.g., 'MON_FN', 'MON_AN').
        faculty_id: The unique ID of the assigned faculty member (e.g., 'FAC01').
    """
    clean_exam = exam_id.strip().upper()
    clean_room = room_code.strip().upper()
    clean_slot = timeslot_id.strip().upper()
    clean_faculty = faculty_id.strip().upper()

    # 1. Input Validation
    if clean_exam not in MOCK_EXAMS:
        return f"Allocation Failed: Exam code '{clean_exam}' does not exist."
    if clean_room not in MOCK_ROOMS:
        return f"Allocation Failed: Room '{clean_room}' does not exist."
    if clean_faculty not in MOCK_INVIGILATORS:
        return f"Allocation Failed: Faculty '{clean_faculty}' does not exist."

    # 2. Capacity Rule check
    student_count = MOCK_EXAMS[clean_exam]["student_count"]
    room_capacity = MOCK_ROOMS[clean_room]["capacity"]

    if student_count > room_capacity:
        return (
            f"Allocation Failed: Room capacity overflow. "
            f"Room {clean_room} can seat {room_capacity} students, but Exam {clean_exam} has {student_count} students registered."
        )

    # 3. Mutate transaction log safely
    new_allocation = {
        "room_code": clean_room,
        "timeslot_id": clean_slot,
        "faculty_id": clean_faculty,
        "exam_id": clean_exam
    }
    MOCK_ALLOCATIONS.append(new_allocation)

    # Update proctor duty counter
    MOCK_INVIGILATORS[clean_faculty]["current_duties"] += 1

    return (
        f"Allocation Success:\n"
        f"- Course scheduled: {clean_exam} ({MOCK_EXAMS[clean_exam]['course_name']})\n"
        f"- Location assigned: Room {clean_room} (Capacity: {room_capacity} students)\n"
        f"- Invigilator assigned: {MOCK_INVIGILATORS[clean_faculty]['name']} (Updated Duties: {MOCK_INVIGILATORS[clean_faculty]['current_duties']}/{MOCK_INVIGILATORS[clean_faculty]['max_duties']})"
    )


# =====================================================================
# 3. CONTEXT INITIALIZATION & COGNITIVE PLANNING
# =====================================================================
def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Fatal Error]: GEMINI_API_KEY environment variable is not defined.")
        sys.exit(1)

    model = LiteLLMModel(
        model_id="gemini/gemini-2.5-flash",
        api_key=api_key
    )

    agent = CodeAgent(
        tools=[check_room_availability, check_invigilator_status, allocate_exam_schedule],
        model=model,
        add_base_tools=False
    )

    # Harder user prompt: Specifically forces the agent to experience environmental
    # failures (R102 is occupied, FAC02 is at limit) and adapt dynamically to find fallbacks.
    user_prompt = (
        "We need to schedule the Engineering Physics (PHY101) exam during the Monday Forenoon (MON_FN) slot. "
        "Your priority is to book Room R102 with Prof. Ratan (FAC02). "
        "If you observe any database conflicts or proctor capacity blockages, integrate that feedback "
        "to adapt your plan. Resolve the allocation by testing fallback rooms (like R101 or LH201) "
        "and alternative proctors (like Prof. Sarah/FAC01) until you secure a valid, conflict-free booking transaction."
    )

    agent.run(user_prompt)


if __name__ == "__main__":
    main()