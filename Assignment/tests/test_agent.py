"""
Unit Tests for Student Support AI Agent
========================================
Tests cover:
- Data handler (attendance, payment, schedule)
- FAQ handler (keyword matching)
- Escalation handler (ticket creation, logging)
- Student data access functions
- Intent classifier (rule-based layer only — LLM tests need API key)
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.student_data import (
    get_student,
    get_all_student_ids,
    get_attendance,
    get_payment_status,
    get_schedule,
)
from agent.data_handler import DataHandler
from agent.faq_handler import FAQHandler
from agent.escalation_handler import EscalationHandler


# ═════════════════════════════════════════════════════════════════════════════
# Data Access Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestStudentData(unittest.TestCase):
    """Test student data access functions."""

    def test_get_student_valid(self):
        """Test retrieving a valid student."""
        student = get_student("A")
        self.assertIsNotNone(student)
        self.assertEqual(student["name"], "Alice Johnson")
        self.assertEqual(student["attended"], 8)
        self.assertEqual(student["total"], 10)
        self.assertEqual(student["payments"], "done")

    def test_get_student_case_insensitive(self):
        """Test that student lookup is case-insensitive."""
        student = get_student("a")
        self.assertIsNotNone(student)
        self.assertEqual(student["name"], "Alice Johnson")

    def test_get_student_invalid(self):
        """Test retrieving a non-existent student."""
        student = get_student("Z")
        self.assertIsNone(student)

    def test_get_all_student_ids(self):
        """Test getting all student IDs."""
        ids = get_all_student_ids()
        self.assertIn("A", ids)
        self.assertIn("B", ids)
        self.assertGreater(len(ids), 0)

    def test_get_attendance_valid(self):
        """Test attendance calculation."""
        attendance = get_attendance("A")
        self.assertIsNotNone(attendance)
        self.assertEqual(attendance["attended"], 8)
        self.assertEqual(attendance["total"], 10)
        self.assertEqual(attendance["percentage"], 80.0)
        self.assertEqual(attendance["status"], "good")

    def test_get_attendance_low(self):
        """Test attendance status for low attendance."""
        attendance = get_attendance("B")
        self.assertIsNotNone(attendance)
        self.assertEqual(attendance["percentage"], 30.0)
        self.assertEqual(attendance["status"], "critical")

    def test_get_attendance_perfect(self):
        """Test attendance for perfect attendance."""
        attendance = get_attendance("C")
        self.assertIsNotNone(attendance)
        self.assertEqual(attendance["percentage"], 100.0)
        self.assertEqual(attendance["status"], "good")

    def test_get_attendance_invalid(self):
        """Test attendance for non-existent student."""
        attendance = get_attendance("Z")
        self.assertIsNone(attendance)

    def test_get_payment_status_done(self):
        """Test payment status for completed payment."""
        payment = get_payment_status("A")
        self.assertIsNotNone(payment)
        self.assertEqual(payment["status"], "done")
        self.assertFalse(payment["is_overdue"])

    def test_get_payment_status_failed(self):
        """Test payment status for failed payment."""
        payment = get_payment_status("B")
        self.assertIsNotNone(payment)
        self.assertEqual(payment["status"], "failed")
        self.assertTrue(payment["is_overdue"])

    def test_get_payment_status_invalid(self):
        """Test payment status for non-existent student."""
        payment = get_payment_status("Z")
        self.assertIsNone(payment)

    def test_get_schedule_valid(self):
        """Test schedule retrieval."""
        schedule = get_schedule("A")
        self.assertIsNotNone(schedule)
        self.assertIn("next_class", schedule)
        self.assertIn("enrolled_courses", schedule)

    def test_get_schedule_invalid(self):
        """Test schedule for non-existent student."""
        schedule = get_schedule("Z")
        self.assertIsNone(schedule)


# ═════════════════════════════════════════════════════════════════════════════
# Data Handler Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestDataHandler(unittest.TestCase):
    """Test the DataHandler business logic."""

    def setUp(self):
        self.handler = DataHandler()

    def test_attendance_query_good(self):
        """Test attendance query for student with good attendance."""
        result = self.handler.handle_attendance_query("A")
        self.assertTrue(result["success"])
        self.assertIn("80.0%", result["message"])
        self.assertIn("Great job", result["message"])
        self.assertFalse(result["needs_attention"])

    def test_attendance_query_critical(self):
        """Test attendance query for student with critical attendance."""
        result = self.handler.handle_attendance_query("B")
        self.assertTrue(result["success"])
        self.assertIn("30.0%", result["message"])
        self.assertIn("critically low", result["message"])
        self.assertTrue(result["needs_attention"])

    def test_attendance_query_invalid_student(self):
        """Test attendance query for non-existent student."""
        result = self.handler.handle_attendance_query("Z")
        self.assertFalse(result["success"])
        self.assertIn("couldn't find", result["message"])

    def test_payment_status_done(self):
        """Test payment status query for completed payment."""
        result = self.handler.handle_payment_status_query("A")
        self.assertTrue(result["success"])
        self.assertIn("Completed", result["message"])
        self.assertFalse(result["needs_escalation"])

    def test_payment_status_failed(self):
        """Test payment status query for failed payment."""
        result = self.handler.handle_payment_status_query("B")
        self.assertTrue(result["success"])
        self.assertIn("Failed", result["message"])
        self.assertTrue(result["needs_escalation"])

    def test_payment_status_pending(self):
        """Test payment status query for pending payment."""
        result = self.handler.handle_payment_status_query("D")
        self.assertTrue(result["success"])
        self.assertIn("Pending", result["message"])
        self.assertFalse(result["needs_escalation"])

    def test_schedule_query(self):
        """Test schedule query."""
        result = self.handler.handle_schedule_query("A")
        self.assertTrue(result["success"])
        self.assertIn("Schedule", result["message"])
        self.assertIn("Python Basics", result["message"])

    def test_student_summary(self):
        """Test student summary generation."""
        summary = self.handler.get_student_summary("A")
        self.assertIsNotNone(summary)
        self.assertIn("Alice Johnson", summary)
        self.assertIn("8/10", summary)


# ═════════════════════════════════════════════════════════════════════════════
# FAQ Handler Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestFAQHandler(unittest.TestCase):
    """Test FAQ handler matching logic."""

    def setUp(self):
        self.handler = FAQHandler()

    def test_booking_faq(self):
        """Test FAQ match for booking query."""
        result = self.handler.find_answer("How do I book a class?")
        self.assertIsNotNone(result)
        self.assertEqual(result["faq_id"], "book_class")
        self.assertIn("Book", result["answer"])

    def test_cancel_faq(self):
        """Test FAQ match for cancellation query."""
        result = self.handler.find_answer("How to cancel my class?")
        self.assertIsNotNone(result)
        self.assertEqual(result["faq_id"], "cancel_class")

    def test_payment_methods_faq(self):
        """Test FAQ match for payment methods."""
        result = self.handler.find_answer("What payment methods do you accept?")
        self.assertIsNotNone(result)
        self.assertEqual(result["faq_id"], "payment_methods")

    def test_refund_faq(self):
        """Test FAQ match for refund policy."""
        result = self.handler.find_answer("What is your refund policy?")
        self.assertIsNotNone(result)
        self.assertEqual(result["faq_id"], "refund_policy")

    def test_no_match(self):
        """Test FAQ when no match is found."""
        result = self.handler.find_answer("What is the meaning of life?")
        self.assertIsNone(result)

    def test_get_all_faqs(self):
        """Test getting all FAQs."""
        faqs = self.handler.get_all_faqs()
        self.assertGreater(len(faqs), 0)
        self.assertIn("question", faqs[0])


# ═════════════════════════════════════════════════════════════════════════════
# Escalation Handler Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEscalationHandler(unittest.TestCase):
    """Test escalation logic and ticket creation."""

    def setUp(self):
        self.handler = EscalationHandler()

    def test_payment_escalation(self):
        """Test escalation for payment failure."""
        result = self.handler.escalate(
            reason="payment_failure",
            student_id="B",
            original_query="My payment failed",
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["priority"], "HIGH")
        self.assertEqual(result["department"], "Billing & Payments")
        self.assertIn("ESC-", result["ticket"]["ticket_id"])

    def test_angry_user_escalation(self):
        """Test escalation for angry user."""
        result = self.handler.escalate(
            reason="angry_user",
            student_id="A",
            original_query="This is terrible service!",
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["priority"], "HIGH")
        self.assertEqual(result["department"], "Student Relations")

    def test_reschedule_escalation(self):
        """Test escalation for reschedule request."""
        result = self.handler.escalate(
            reason="reschedule",
            student_id="A",
            original_query="I want to reschedule my class",
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["priority"], "MEDIUM")

    def test_unknown_query_escalation(self):
        """Test escalation for unknown query."""
        result = self.handler.escalate(
            reason="unknown_query",
            student_id=None,
            original_query="Some random question",
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["priority"], "LOW")

    def test_escalation_log(self):
        """Test that escalations are logged."""
        self.handler.escalate(reason="payment_failure", original_query="test1")
        self.handler.escalate(reason="angry_user", original_query="test2")
        log = self.handler.get_escalation_log()
        self.assertEqual(len(log), 2)

    def test_escalation_stats(self):
        """Test escalation statistics."""
        self.handler.escalate(reason="payment_failure", original_query="test1")
        self.handler.escalate(reason="payment_failure", original_query="test2")
        self.handler.escalate(reason="angry_user", original_query="test3")
        stats = self.handler.get_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["by_priority"]["HIGH"], 3)

    def test_invalid_reason_defaults(self):
        """Test that invalid reason defaults to unknown_query."""
        result = self.handler.escalate(
            reason="invalid_reason",
            original_query="test",
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["priority"], "LOW")  # unknown_query is LOW


# ═════════════════════════════════════════════════════════════════════════════
# Intent Classifier Tests (Rule-based only — no API needed)
# ═════════════════════════════════════════════════════════════════════════════

class TestIntentClassifierRules(unittest.TestCase):
    """Test rule-based intent classification (no API key required)."""

    def test_keyword_patterns(self):
        """Test that keyword patterns are defined correctly."""
        from agent.intent_classifier import KEYWORD_RULES
        self.assertIn("attendance_query", KEYWORD_RULES)
        self.assertIn("payment_issue", KEYWORD_RULES)
        self.assertIn("reschedule_request", KEYWORD_RULES)
        self.assertIn("booking_query", KEYWORD_RULES)

    def test_angry_patterns(self):
        """Test angry sentiment detection patterns."""
        from agent.intent_classifier import ANGRY_PATTERNS, ANGRY_PATTERNS_CASE_SENSITIVE
        import re

        def is_angry(text):
            """Check both case-insensitive and case-sensitive patterns."""
            if any(re.search(p, text, re.IGNORECASE) for p in ANGRY_PATTERNS):
                return True
            if any(re.search(p, text) for p in ANGRY_PATTERNS_CASE_SENSITIVE):
                return True
            return False

        # Should match angry patterns
        angry_texts = [
            "This is terrible service!",
            "I am so frustrated with this system",
            "You are pathetic",
            "THIS IS UNACCEPTABLE!!!",
            "I want to talk to a human",
            "WHAT IS WRONG WITH YOU PEOPLE",  # ALL CAPS
        ]
        for text in angry_texts:
            self.assertTrue(is_angry(text), f"Should detect anger in: {text}")

        # Should NOT match
        calm_texts = [
            "What is my attendance?",
            "Thank you for your help",
            "How do I book a class?",
            "Hello there",
        ]
        for text in calm_texts:
            self.assertFalse(is_angry(text), f"Should NOT detect anger in: {text}")


# ═════════════════════════════════════════════════════════════════════════════
# Edge Case Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_student_id(self):
        """Test with empty student ID."""
        self.assertIsNone(get_student(""))

    def test_special_characters_in_id(self):
        """Test with special characters in student ID."""
        self.assertIsNone(get_student("!@#"))

    def test_attendance_percentage_calculation(self):
        """Test edge case of attendance percentage calculation."""
        attendance = get_attendance("C")  # 10/10
        self.assertEqual(attendance["percentage"], 100.0)

    def test_data_handler_with_all_students(self):
        """Test data handler works for ALL students."""
        handler = DataHandler()
        for student_id in get_all_student_ids():
            result = handler.handle_attendance_query(student_id)
            self.assertTrue(result["success"], f"Failed for student {student_id}")
            result = handler.handle_payment_status_query(student_id)
            self.assertTrue(result["success"], f"Failed for student {student_id}")
            result = handler.handle_schedule_query(student_id)
            self.assertTrue(result["success"], f"Failed for student {student_id}")

    def test_faq_partial_match(self):
        """Test FAQ with partial keyword matches."""
        handler = FAQHandler()
        result = handler.find_answer("booking")
        self.assertIsNotNone(result)

    def test_escalation_ticket_unique_ids(self):
        """Test that escalation tickets get unique IDs."""
        handler = EscalationHandler()
        r1 = handler.escalate(reason="payment_failure", original_query="test1")
        r2 = handler.escalate(reason="payment_failure", original_query="test2")
        self.assertNotEqual(
            r1["ticket"]["ticket_id"],
            r2["ticket"]["ticket_id"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
