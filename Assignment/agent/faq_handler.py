"""
FAQ Handler Module
==================
Handles frequently asked questions with predefined responses.
These are static responses that don't require data lookup or AI.

In production, these could be loaded from a database or CMS.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ─── FAQ Knowledge Base ──────────────────────────────────────────────────────
# Each FAQ has: keywords (for matching), question, and answer.

FAQ_DATABASE = [
    {
        "id": "book_class",
        "keywords": ["book", "booking", "enroll", "registration", "sign up", "join"],
        "question": "How do I book a class?",
        "answer": (
            "📖 **How to Book a Class**\n\n"
            "Follow these simple steps:\n"
            "1. Log in to the **Student Portal** at portal.academy.com\n"
            "2. Navigate to **Courses → Browse Available**\n"
            "3. Select your desired course and click **Enroll Now**\n"
            "4. Choose your preferred time slot\n"
            "5. Complete the payment to confirm your booking\n\n"
            "💡 **Tip:** Book early — popular time slots fill up fast!\n"
            "Need help? Feel free to ask me anything else."
        ),
    },
    {
        "id": "cancel_class",
        "keywords": ["cancel", "cancellation", "drop", "withdraw"],
        "question": "How do I cancel a class?",
        "answer": (
            "🚫 **Class Cancellation Policy**\n\n"
            "To cancel a class:\n"
            "1. Go to **My Classes** in the Student Portal\n"
            "2. Select the class you want to cancel\n"
            "3. Click **Cancel Enrollment**\n\n"
            "⚠️ **Important:**\n"
            "• Free cancellation up to **24 hours** before the class\n"
            "• Late cancellations may incur a fee\n"
            "• Refunds are processed within 5-7 business days\n\n"
            "For urgent cancellations, I can escalate to our support team."
        ),
    },
    {
        "id": "payment_methods",
        "keywords": ["payment method", "pay", "payment option", "card", "upi", "how to pay"],
        "question": "What payment methods are accepted?",
        "answer": (
            "💳 **Accepted Payment Methods**\n\n"
            "We accept the following payment methods:\n"
            "• **Credit/Debit Cards** (Visa, Mastercard, RuPay)\n"
            "• **UPI** (Google Pay, PhonePe, Paytm)\n"
            "• **Net Banking** (All major banks)\n"
            "• **EMI** (Available on select cards for courses above ₹5,000)\n\n"
            "All transactions are secured with **256-bit SSL encryption**. 🔒"
        ),
    },
    {
        "id": "contact_support",
        "keywords": ["contact", "support", "help", "phone", "email", "reach"],
        "question": "How do I contact support?",
        "answer": (
            "📞 **Contact Our Support Team**\n\n"
            "You can reach us through:\n"
            "• **Email:** support@academy.com\n"
            "• **Phone:** +91-1800-XXX-XXXX (Mon-Fri, 9AM-6PM)\n"
            "• **Live Chat:** Available on the Student Portal\n"
            "• **WhatsApp:** +91-98XXX-XXXXX\n\n"
            "⏱️ Average response time: **Under 2 hours** during business hours."
        ),
    },
    {
        "id": "attendance_policy",
        "keywords": ["attendance policy", "minimum attendance", "attendance requirement"],
        "question": "What is the attendance policy?",
        "answer": (
            "📋 **Attendance Policy**\n\n"
            "• **Minimum required attendance:** 75%\n"
            "• Below 75% → Warning notification sent\n"
            "• Below 50% → Risk of course incompletion\n"
            "• Medical leaves can be applied separately\n\n"
            "💡 Attendance is tracked automatically when you join the live class.\n"
            "Check your attendance anytime by asking me!"
        ),
    },
    {
        "id": "certificate",
        "keywords": ["certificate", "certification", "completion", "diploma"],
        "question": "How do I get my certificate?",
        "answer": (
            "🎓 **Certificates**\n\n"
            "To receive your course completion certificate:\n"
            "1. Maintain **75% or higher attendance**\n"
            "2. Complete all **assignments and assessments**\n"
            "3. Score at least **60%** in the final evaluation\n\n"
            "📩 Certificates are emailed within **7 days** of course completion.\n"
            "Digital certificates can also be downloaded from the Student Portal."
        ),
    },
    {
        "id": "refund_policy",
        "keywords": ["refund", "money back", "return", "reimburse"],
        "question": "What is the refund policy?",
        "answer": (
            "💰 **Refund Policy**\n\n"
            "• **Full refund:** Within 7 days of enrollment (no classes attended)\n"
            "• **50% refund:** Within 14 days (attended less than 3 classes)\n"
            "• **No refund:** After 14 days or more than 3 classes attended\n\n"
            "To request a refund, contact support@academy.com with your enrollment ID.\n"
            "Refunds are processed within **5-7 business days**."
        ),
    },
]


class FAQHandler:
    """Handles FAQ queries by matching against the knowledge base."""

    def __init__(self):
        self.faqs = FAQ_DATABASE

    def find_answer(self, query: str) -> Optional[dict]:
        """
        Search for a matching FAQ based on the user's query.

        Args:
            query: User's question

        Returns:
            Dict with question and answer if found, None otherwise
        """
        query_lower = query.lower()
        best_match = None
        best_score = 0

        for faq in self.faqs:
            score = 0
            for keyword in faq["keywords"]:
                if keyword in query_lower:
                    score += 1
                    # Bonus for exact phrase match
                    if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                        score += 0.5

            if score > best_score:
                best_score = score
                best_match = faq

        if best_match and best_score >= 1:
            logger.info("FAQ match found: %s (score: %.1f)", best_match["id"], best_score)
            return {
                "question": best_match["question"],
                "answer": best_match["answer"],
                "faq_id": best_match["id"],
                "confidence": min(best_score / 3, 1.0),
            }

        logger.debug("No FAQ match found for query: %s", query[:50])
        return None

    def get_all_faqs(self) -> list[dict]:
        """Return all available FAQs (for display in help menu)."""
        return [
            {"question": faq["question"], "id": faq["id"]}
            for faq in self.faqs
        ]
