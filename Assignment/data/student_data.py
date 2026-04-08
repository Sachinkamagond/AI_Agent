"""
Student data store and query functions.
In production, this would connect to a database.
For this demo, we use in-memory dictionaries.
"""

from typing import Optional


# ─── Sample Student Records ─────────────────────────────────────────────────
# Each student has: name, attended classes, total classes, payment status,
# enrolled courses, and contact info.

STUDENTS = {
    "A": {
        "name": "Alice Johnson",
        "attended": 8,
        "total": 10,
        "payments": "done",
        "enrolled_courses": ["Python Basics", "Data Science 101"],
        "email": "alice@example.com",
        "next_class": "2026-04-10 10:00 AM - Python Basics",
    },
    "B": {
        "name": "Bob Smith",
        "attended": 3,
        "total": 10,
        "payments": "failed",
        "enrolled_courses": ["Web Development", "ML Fundamentals"],
        "email": "bob@example.com",
        "next_class": "2026-04-10 02:00 PM - Web Development",
    },
    "C": {
        "name": "Charlie Davis",
        "attended": 10,
        "total": 10,
        "payments": "done",
        "enrolled_courses": ["Advanced Python", "Cloud Computing"],
        "email": "charlie@example.com",
        "next_class": "2026-04-11 09:00 AM - Advanced Python",
    },
    "D": {
        "name": "Diana Lee",
        "attended": 5,
        "total": 10,
        "payments": "pending",
        "enrolled_courses": ["Data Science 101"],
        "email": "diana@example.com",
        "next_class": "2026-04-11 11:00 AM - Data Science 101",
    },
}


# ─── Data Access Functions ───────────────────────────────────────────────────

def get_student(student_id: str) -> Optional[dict]:
    """Retrieve a student record by ID (case-insensitive)."""
    return STUDENTS.get(student_id.upper())


def get_all_student_ids() -> list[str]:
    """Return all available student IDs."""
    return list(STUDENTS.keys())


def get_attendance(student_id: str) -> Optional[dict]:
    """
    Calculate attendance details for a student.
    Returns dict with attended, total, percentage, and status.
    """
    student = get_student(student_id)
    if not student:
        return None

    attended = student["attended"]
    total = student["total"]
    percentage = round((attended / total) * 100, 1) if total > 0 else 0.0

    # Determine attendance status
    if percentage >= 75:
        status = "good"
    elif percentage >= 50:
        status = "warning"
    else:
        status = "critical"

    return {
        "attended": attended,
        "total": total,
        "percentage": percentage,
        "status": status,
        "name": student["name"],
    }


def get_payment_status(student_id: str) -> Optional[dict]:
    """Retrieve payment status for a student."""
    student = get_student(student_id)
    if not student:
        return None

    return {
        "status": student["payments"],
        "name": student["name"],
        "is_overdue": student["payments"] == "failed",
    }


def get_schedule(student_id: str) -> Optional[dict]:
    """Retrieve schedule information for a student."""
    student = get_student(student_id)
    if not student:
        return None

    return {
        "name": student["name"],
        "next_class": student["next_class"],
        "enrolled_courses": student["enrolled_courses"],
    }
