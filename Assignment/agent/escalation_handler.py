"""
Escalation Handler Module
=========================
Manages the escalation logic for queries that require human intervention.

Escalation is triggered for:
- Payment failures (billing issue)
- Angry / frustrated users (sentiment-based)
- Unknown queries the agent can't handle
- Explicit requests for human agent
- Reschedule requests (requires human coordination)
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Escalation Categories ───────────────────────────────────────────────────

ESCALATION_REASONS = {
    "payment_failure": {
        "priority": "HIGH",
        "department": "Billing & Payments",
        "sla": "2 hours",
        "message": (
            "🚨 **Escalating to Billing Team**\n\n"
            "Your payment issue has been flagged as **HIGH PRIORITY** "
            "and escalated to our Billing & Payments department.\n\n"
            "📋 **What happens next:**\n"
            "  • A billing specialist will review your case\n"
            "  • You'll receive an email confirmation shortly\n"
            "  • Expected resolution: **within 2 hours**\n\n"
            "📞 For urgent help, call: +91-1800-XXX-XXXX (Option 2)"
        ),
    },
    "angry_user": {
        "priority": "HIGH",
        "department": "Student Relations",
        "sla": "1 hour",
        "message": (
            "🤝 **Connecting you with a Support Specialist**\n\n"
            "I understand your frustration, and I sincerely apologize for the inconvenience. "
            "I'm escalating this to our **Student Relations team** right away.\n\n"
            "📋 **What happens next:**\n"
            "  • A senior support specialist will reach out to you\n"
            "  • Your case is marked as **HIGH PRIORITY**\n"
            "  • Expected response: **within 1 hour**\n\n"
            "Your experience matters to us. Thank you for your patience."
        ),
    },
    "reschedule": {
        "priority": "MEDIUM",
        "department": "Academic Coordination",
        "sla": "4 hours",
        "message": (
            "📅 **Rescheduling Request Noted**\n\n"
            "I've forwarded your rescheduling request to our "
            "**Academic Coordination team**.\n\n"
            "📋 **What happens next:**\n"
            "  • A coordinator will check available time slots\n"
            "  • You'll receive options via email within **4 hours**\n"
            "  • You can confirm your preferred new slot\n\n"
            "💡 **Tip:** You can also check available slots on the Student Portal "
            "under **My Classes → Reschedule**."
        ),
    },
    "unknown_query": {
        "priority": "LOW",
        "department": "General Support",
        "sla": "24 hours",
        "message": (
            "🔄 **Connecting you with our Support Team**\n\n"
            "I wasn't able to fully address your query, so I'm "
            "connecting you with a **human support agent** who can help better.\n\n"
            "📋 **What happens next:**\n"
            "  • Your query has been logged for review\n"
            "  • A support agent will assist you within **24 hours**\n"
            "  • You'll be contacted via your registered email\n\n"
            "Is there anything else I can help you with in the meantime?"
        ),
    },
    "technical_issue": {
        "priority": "MEDIUM",
        "department": "Technical Support",
        "sla": "4 hours",
        "message": (
            "🔧 **Technical Issue Reported**\n\n"
            "I've logged your technical issue and escalated it to our "
            "**Technical Support team**.\n\n"
            "📋 **What happens next:**\n"
            "  • A technician will investigate the issue\n"
            "  • Expected resolution: **within 4 hours**\n"
            "  • You'll receive updates via email\n\n"
            "🔄 In the meantime, try:\n"
            "  • Clearing your browser cache\n"
            "  • Using a different browser\n"
            "  • Checking your internet connection"
        ),
    },
}


class EscalationTicket:
    """Represents an escalation ticket."""

    _ticket_counter = 1000

    def __init__(
        self,
        reason: str,
        student_id: Optional[str],
        original_query: str,
        priority: str,
        department: str,
        sla: str,
    ):
        EscalationTicket._ticket_counter += 1
        self.ticket_id = f"ESC-{EscalationTicket._ticket_counter}"
        self.reason = reason
        self.student_id = student_id
        self.original_query = original_query
        self.priority = priority
        self.department = department
        self.sla = sla
        self.created_at = datetime.now()
        self.status = "OPEN"

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "reason": self.reason,
            "student_id": self.student_id,
            "original_query": self.original_query,
            "priority": self.priority,
            "department": self.department,
            "sla": self.sla,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }

    def __repr__(self):
        return f"EscalationTicket({self.ticket_id}, {self.priority}, {self.department})"


class EscalationHandler:
    """
    Manages escalation decisions and ticket creation.
    Maintains a log of all escalations for audit purposes.
    """

    def __init__(self):
        self.escalation_log: list[EscalationTicket] = []

    def escalate(
        self,
        reason: str,
        student_id: Optional[str] = None,
        original_query: str = "",
        context: Optional[dict] = None,
    ) -> dict:
        """
        Create an escalation ticket and return the response.

        Args:
            reason: One of the ESCALATION_REASONS keys
            student_id: The student's ID (if identified)
            original_query: The original user query
            context: Additional context (intent classification, etc.)

        Returns:
            Dict with escalation message, ticket info, and metadata
        """
        if reason not in ESCALATION_REASONS:
            reason = "unknown_query"

        escalation_info = ESCALATION_REASONS[reason]

        # Create ticket
        ticket = EscalationTicket(
            reason=reason,
            student_id=student_id,
            original_query=original_query,
            priority=escalation_info["priority"],
            department=escalation_info["department"],
            sla=escalation_info["sla"],
        )

        # Log the escalation
        self.escalation_log.append(ticket)
        logger.warning(
            "ESCALATION CREATED: %s | Reason: %s | Priority: %s | Student: %s",
            ticket.ticket_id, reason, escalation_info["priority"], student_id,
        )

        # Build response
        ticket_info = (
            f"\n\n---\n"
            f"🎫 **Ticket ID:** {ticket.ticket_id}\n"
            f"⏱️ **SLA:** {escalation_info['sla']}\n"
            f"🏢 **Department:** {escalation_info['department']}\n"
            f"🔴 **Priority:** {escalation_info['priority']}"
        )

        return {
            "message": escalation_info["message"] + ticket_info,
            "ticket": ticket.to_dict(),
            "escalated": True,
            "priority": escalation_info["priority"],
            "department": escalation_info["department"],
        }

    def get_escalation_log(self) -> list[dict]:
        """Return the full escalation log."""
        return [ticket.to_dict() for ticket in self.escalation_log]

    def get_stats(self) -> dict:
        """Get escalation statistics."""
        if not self.escalation_log:
            return {"total": 0, "by_priority": {}, "by_department": {}}

        by_priority = {}
        by_department = {}
        for ticket in self.escalation_log:
            by_priority[ticket.priority] = by_priority.get(ticket.priority, 0) + 1
            by_department[ticket.department] = by_department.get(ticket.department, 0) + 1

        return {
            "total": len(self.escalation_log),
            "by_priority": by_priority,
            "by_department": by_department,
        }
