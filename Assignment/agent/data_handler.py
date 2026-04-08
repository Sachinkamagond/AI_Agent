"""
Data Handler Module
===================
Handles queries that require looking up student data,
such as attendance percentages and payment status.

This module contains the business logic for data-driven responses,
NOT just raw data retrieval.
"""

import logging
from typing import Optional
from data.student_data import get_attendance, get_payment_status, get_schedule, get_student

logger = logging.getLogger(__name__)


class DataHandler:
    """Handles data-related queries with smart formatting and insights."""

    def handle_attendance_query(self, student_id: str) -> dict:
        """
        Process an attendance query for a student.

        Returns a dict with:
            - success: bool
            - message: formatted response string
            - data: raw attendance data
            - needs_attention: bool (if attendance is low)
        """
        attendance = get_attendance(student_id)

        if not attendance:
            return {
                "success": False,
                "message": f"❌ Sorry, I couldn't find records for student ID '{student_id}'. "
                           f"Please check the student ID and try again.",
                "data": None,
                "needs_attention": False,
            }

        name = attendance["name"]
        attended = attendance["attended"]
        total = attendance["total"]
        percentage = attendance["percentage"]
        status = attendance["status"]

        # Build contextual response based on attendance status
        if status == "good":
            emoji = "✅"
            status_msg = "Great job! Your attendance is on track."
            advice = "Keep it up! 💪"
        elif status == "warning":
            emoji = "⚠️"
            status_msg = "Your attendance needs improvement."
            advice = (
                "I'd recommend attending all remaining classes to improve your standing. "
                "You need at least 75% attendance for course completion."
            )
        else:  # critical
            emoji = "🚨"
            status_msg = "Your attendance is critically low!"
            advice = (
                "This is urgent — you may face academic consequences. "
                "Please contact your course coordinator immediately. "
                "I'm also flagging this for follow-up with our support team."
            )

        message = (
            f"{emoji} **Attendance Report for {name}**\n\n"
            f"📊 Classes Attended: **{attended} / {total}**\n"
            f"📈 Attendance Percentage: **{percentage}%**\n"
            f"📋 Status: **{status.upper()}**\n\n"
            f"{status_msg}\n{advice}"
        )

        return {
            "success": True,
            "message": message,
            "data": attendance,
            "needs_attention": status in ("warning", "critical"),
        }

    def handle_payment_status_query(self, student_id: str) -> dict:
        """
        Process a payment status query for a student.

        Returns a dict with:
            - success: bool
            - message: formatted response
            - data: raw payment data
            - needs_escalation: bool (if payment has failed)
        """
        payment = get_payment_status(student_id)

        if not payment:
            return {
                "success": False,
                "message": f"❌ Sorry, I couldn't find payment records for student ID '{student_id}'.",
                "data": None,
                "needs_escalation": False,
            }

        name = payment["name"]
        status = payment["status"]

        if status == "done":
            message = (
                f"✅ **Payment Status for {name}**\n\n"
                f"💳 Status: **Completed** ✔️\n"
                f"Your payment is up to date. No action needed!"
            )
            needs_escalation = False

        elif status == "pending":
            message = (
                f"⏳ **Payment Status for {name}**\n\n"
                f"💳 Status: **Pending**\n"
                f"Your payment is being processed. If it's been more than 48 hours, "
                f"please contact our billing team or I can escalate this for you."
            )
            needs_escalation = False

        else:  # failed
            message = (
                f"🚨 **Payment Status for {name}**\n\n"
                f"💳 Status: **Failed** ❌\n\n"
                f"Your payment has failed. This could be due to:\n"
                f"  • Insufficient funds\n"
                f"  • Card declined by bank\n"
                f"  • Network issues during transaction\n\n"
                f"🔄 **I'm escalating this to our billing team** for immediate assistance.\n"
                f"They will contact you at your registered email."
            )
            needs_escalation = True

        return {
            "success": True,
            "message": message,
            "data": payment,
            "needs_escalation": needs_escalation,
        }

    def handle_schedule_query(self, student_id: str) -> dict:
        """
        Process a schedule query for a student.

        Returns a dict with:
            - success: bool
            - message: formatted response
            - data: raw schedule data
        """
        schedule = get_schedule(student_id)

        if not schedule:
            return {
                "success": False,
                "message": f"❌ Sorry, I couldn't find schedule information for student ID '{student_id}'.",
                "data": None,
            }

        name = schedule["name"]
        next_class = schedule["next_class"]
        courses = ", ".join(schedule["enrolled_courses"])

        message = (
            f"📅 **Schedule for {name}**\n\n"
            f"📚 Enrolled Courses: **{courses}**\n"
            f"⏰ Next Class: **{next_class}**\n\n"
            f"Need to reschedule? Just let me know!"
        )

        return {
            "success": True,
            "message": message,
            "data": schedule,
        }

    def get_student_summary(self, student_id: str) -> Optional[str]:
        """Get a brief summary of the student for context."""
        student = get_student(student_id)
        if not student:
            return None
        return (
            f"Student: {student['name']} | "
            f"Attendance: {student['attended']}/{student['total']} | "
            f"Payment: {student['payments']}"
        )
