"""
Student Support Agent — Main Orchestrator
==========================================
This is the CORE of the agent. It implements the Decision Engine
that routes user queries to appropriate handlers based on:
  1. Classified intent (from IntentClassifier)
  2. Sentiment analysis (angry users get escalated)
  3. Student context (identified student's data)
  4. Conversation history

KEY DESIGN PRINCIPLE: Decision logic is EXPLICIT Python code,
NOT just an LLM passthrough. The LLM assists with classification
and generating natural responses, but routing decisions are
controlled by deterministic business rules.
"""

import logging
from typing import Optional

from google import genai

from config import Config
from agent.intent_classifier import IntentClassifier, IntentClassificationResult
from agent.data_handler import DataHandler
from agent.faq_handler import FAQHandler
from agent.escalation_handler import EscalationHandler
from data.student_data import get_student, get_all_student_ids

logger = logging.getLogger(__name__)


class ConversationMessage:
    """Represents a single message in the conversation."""

    def __init__(self, role: str, content: str, metadata: Optional[dict] = None):
        self.role = role  # "user" or "agent"
        self.content = content
        self.metadata = metadata or {}


class StudentSupportAgent:
    """
    Main AI Agent Orchestrator.

    Manages conversation flow, routes queries to handlers,
    and maintains conversation state.

    Decision Flow:
    ┌─────────────┐
    │  User Input  │
    └──────┬──────┘
           ▼
    ┌─────────────────┐
    │ Intent Classifier│ (Rule-based + Gemini)
    └──────┬──────────┘
           ▼
    ┌─────────────────┐      ┌──────────────┐
    │ Decision Engine  │─────►│  Escalation? │
    │ (Python Logic)   │      └──────┬───────┘
    └──────┬──────────┘              │
           ▼                         ▼
    ┌──────────────┐          ┌────────────┐
    │ Route Handler│          │ Escalation │
    │  - Data      │          │  Handler   │
    │  - FAQ       │          └────────────┘
    │  - General   │
    └──────────────┘
    """

    def __init__(self, student_id: Optional[str] = None):
        """
        Initialize the agent with all handler modules.

        Args:
            student_id: Optional pre-set student ID for context
        """
        Config.validate()

        # Initialize handler modules
        self.classifier = IntentClassifier()
        self.data_handler = DataHandler()
        self.faq_handler = FAQHandler()
        self.escalation_handler = EscalationHandler()

        # Initialize Gemini client for general conversations
        self.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.gemini_model_name = Config.GEMINI_MODEL

        # Conversation state
        self.student_id: Optional[str] = student_id
        self.conversation_history: list[ConversationMessage] = []
        self.identified: bool = student_id is not None

        logger.info(
            "StudentSupportAgent initialized. Student: %s",
            student_id or "Not identified",
        )

    def set_student(self, student_id: str) -> str:
        """
        Set the active student for this conversation.

        Args:
            student_id: The student ID to set

        Returns:
            Confirmation message
        """
        student = get_student(student_id)
        if student:
            self.student_id = student_id.upper()
            self.identified = True
            logger.info("Student identified: %s (%s)", student_id, student["name"])
            return (
                f"✅ Welcome, **{student['name']}**! I've loaded your profile.\n"
                f"How can I help you today?"
            )
        else:
            available = ", ".join(get_all_student_ids())
            return (
                f"❌ Student ID '{student_id}' not found.\n"
                f"Available student IDs: **{available}**\n"
                f"Please try again."
            )

    def process_query(self, query: str) -> dict:
        """
        Main entry point: Process a user query and return a response.

        This method implements the core DECISION ENGINE.

        Args:
            query: The user's input text

        Returns:
            Dict with:
                - response: str (the agent's reply)
                - intent: str (classified intent)
                - sentiment: str (detected sentiment)
                - escalated: bool (whether this was escalated)
                - decision_reasoning: str (why this decision was made)
                - classification_details: dict (full classification info)
        """
        # Add user message to history
        self.conversation_history.append(ConversationMessage("user", query))

        # ── Step 1: Classify the intent ──────────────────────────────────────
        classification = self.classifier.classify(query)
        logger.info("Classification result: %s", classification)

        # ── Step 2: Decision Engine — Route based on intent + sentiment ──────
        response_data = self._make_decision(query, classification)

        # ── Step 3: Add agent response to history ────────────────────────────
        self.conversation_history.append(
            ConversationMessage(
                "agent",
                response_data["response"],
                metadata={"intent": classification.intent},
            )
        )

        # Trim history if too long
        if len(self.conversation_history) > Config.MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[-Config.MAX_CONVERSATION_HISTORY:]

        return response_data

    def _make_decision(self, query: str, classification: IntentClassificationResult) -> dict:
        """
        ┌─────────────────────────────────────────────────────────────────────┐
        │                      DECISION ENGINE                                │
        │                                                                     │
        │  This is the CORE decision-making logic of the agent.               │
        │  It uses explicit Python rules — NOT just LLM passthrough.          │
        │                                                                     │
        │  Priority order:                                                    │
        │  1. Check for ANGRY sentiment → Escalate                            │
        │  2. Check for ESCALATION intents → Escalate                         │
        │  3. Check for DATA queries → Answer from data                       │
        │  4. Check for FAQ matches → Answer from FAQ                         │
        │  5. Handle GREETINGS / FAREWELLS                                    │
        │  6. Fallback → Use Gemini for general response, then escalate       │
        └─────────────────────────────────────────────────────────────────────┘
        """
        intent = classification.intent
        sentiment = classification.sentiment

        # ── RULE 1: Angry user → ALWAYS escalate (regardless of intent) ──────
        if sentiment == "angry":
            logger.warning("DECISION: Angry user detected — escalating")
            escalation = self.escalation_handler.escalate(
                reason="angry_user",
                student_id=self.student_id,
                original_query=query,
                context=classification.to_dict(),
            )
            # If there's a data component, include that too
            data_addendum = ""
            if intent == "attendance_query" and self.student_id:
                result = self.data_handler.handle_attendance_query(self.student_id)
                if result["success"]:
                    data_addendum = f"\n\nHere's your information while we connect you:\n\n{result['message']}"

            return {
                "response": escalation["message"] + data_addendum,
                "intent": intent,
                "sentiment": sentiment,
                "escalated": True,
                "decision_reasoning": (
                    f"User sentiment is ANGRY. Escalating to human agent regardless of "
                    f"intent ({intent}). Priority: {escalation['priority']}"
                ),
                "classification_details": classification.to_dict(),
            }

        # ── RULE 2: Payment issue → ALWAYS escalate (critical business rule) ─
        if intent == "payment_issue":
            logger.warning("DECISION: Payment issue — escalating to billing")
            escalation = self.escalation_handler.escalate(
                reason="payment_failure",
                student_id=self.student_id,
                original_query=query,
                context=classification.to_dict(),
            )
            return {
                "response": escalation["message"],
                "intent": intent,
                "sentiment": sentiment,
                "escalated": True,
                "decision_reasoning": (
                    "Payment issue detected. Business rule: ALL payment issues "
                    "are escalated to billing team immediately."
                ),
                "classification_details": classification.to_dict(),
            }

        # ── RULE 3: Complaint → Escalate ─────────────────────────────────────
        if intent == "complaint":
            logger.warning("DECISION: Complaint — escalating")
            escalation = self.escalation_handler.escalate(
                reason="angry_user",
                student_id=self.student_id,
                original_query=query,
                context=classification.to_dict(),
            )
            return {
                "response": escalation["message"],
                "intent": intent,
                "sentiment": sentiment,
                "escalated": True,
                "decision_reasoning": (
                    "User is filing a complaint. Escalating to Student Relations "
                    "for resolution."
                ),
                "classification_details": classification.to_dict(),
            }

        # ── RULE 4: Reschedule → Acknowledge + Escalate ──────────────────────
        if intent == "reschedule_request":
            logger.info("DECISION: Reschedule request — acknowledging and escalating")
            escalation = self.escalation_handler.escalate(
                reason="reschedule",
                student_id=self.student_id,
                original_query=query,
                context=classification.to_dict(),
            )
            return {
                "response": escalation["message"],
                "intent": intent,
                "sentiment": sentiment,
                "escalated": True,
                "decision_reasoning": (
                    "Reschedule requests require human coordination. "
                    "Acknowledging request and escalating to Academic Coordination."
                ),
                "classification_details": classification.to_dict(),
            }

        # ── RULE 5: Attendance query → Answer from data ──────────────────────
        if intent == "attendance_query":
            return self._handle_data_query("attendance", query, classification)

        # ── RULE 6: Payment status → Check data, maybe escalate ──────────────
        if intent == "payment_status":
            return self._handle_data_query("payment", query, classification)

        # ── RULE 7: Schedule query → Answer from data ────────────────────────
        if intent == "schedule_query":
            return self._handle_data_query("schedule", query, classification)

        # ── RULE 8: Booking / FAQ → Static response ─────────────────────────
        if intent in ("booking_query", "faq"):
            return self._handle_faq_query(query, classification)

        # ── RULE 9: Greeting → Friendly response ────────────────────────────
        if intent == "greeting":
            return self._handle_greeting(classification)

        # ── RULE 10: Farewell → Goodbye response ────────────────────────────
        if intent == "farewell":
            return self._handle_farewell(classification)

        # ── RULE 11: Unknown → Try Gemini, then escalate ────────────────────
        return self._handle_unknown(query, classification)

    def _handle_data_query(
        self, query_type: str, query: str, classification: IntentClassificationResult
    ) -> dict:
        """Handle data-driven queries (attendance, payment, schedule)."""
        if not self.student_id:
            available = ", ".join(get_all_student_ids())
            return {
                "response": (
                    f"👤 I'd love to help with your {query_type} information, "
                    f"but I need to know which student you are first.\n\n"
                    f"Available student IDs: **{available}**\n"
                    f"Please tell me your student ID."
                ),
                "intent": classification.intent,
                "sentiment": classification.sentiment,
                "escalated": False,
                "decision_reasoning": (
                    f"Data query ({query_type}) but student not identified. "
                    f"Asking for student ID before proceeding."
                ),
                "classification_details": classification.to_dict(),
            }

        # Route to specific data handler
        if query_type == "attendance":
            result = self.data_handler.handle_attendance_query(self.student_id)
            reasoning = "Attendance query with identified student. Answered from data."
        elif query_type == "payment":
            result = self.data_handler.handle_payment_status_query(self.student_id)
            reasoning = "Payment status query with identified student. Checking data."
            # If payment failed, add escalation
            if result.get("needs_escalation"):
                escalation = self.escalation_handler.escalate(
                    reason="payment_failure",
                    student_id=self.student_id,
                    original_query=query,
                )
                result["message"] += "\n\n" + escalation["message"]
                return {
                    "response": result["message"],
                    "intent": classification.intent,
                    "sentiment": classification.sentiment,
                    "escalated": True,
                    "decision_reasoning": (
                        "Payment status check revealed FAILED payment. "
                        "Auto-escalating to billing team."
                    ),
                    "classification_details": classification.to_dict(),
                }
        else:  # schedule
            result = self.data_handler.handle_schedule_query(self.student_id)
            reasoning = "Schedule query with identified student. Answered from data."

        return {
            "response": result["message"],
            "intent": classification.intent,
            "sentiment": classification.sentiment,
            "escalated": False,
            "decision_reasoning": reasoning,
            "classification_details": classification.to_dict(),
        }

    def _handle_faq_query(
        self, query: str, classification: IntentClassificationResult
    ) -> dict:
        """Handle FAQ queries from the knowledge base."""
        faq_result = self.faq_handler.find_answer(query)

        if faq_result:
            return {
                "response": faq_result["answer"],
                "intent": classification.intent,
                "sentiment": classification.sentiment,
                "escalated": False,
                "decision_reasoning": (
                    f"FAQ match found: '{faq_result['question']}' "
                    f"(confidence: {faq_result['confidence']:.2f}). "
                    f"Responding with pre-defined answer."
                ),
                "classification_details": classification.to_dict(),
            }

        # No FAQ match — try Gemini for a general answer
        return self._handle_with_gemini(query, classification, "faq")

    def _handle_greeting(self, classification: IntentClassificationResult) -> dict:
        """Handle greeting messages."""
        if self.student_id:
            from data.student_data import get_student
            student = get_student(self.student_id)
            name = student["name"] if student else "there"
            response = (
                f"👋 Hello, **{name}**! Welcome back!\n\n"
                f"I'm your Student Support Assistant. Here's what I can help with:\n"
                f"• 📊 Check your **attendance**\n"
                f"• 💳 View your **payment status**\n"
                f"• 📅 Check your **class schedule**\n"
                f"• 📖 Answer **FAQs** about booking, policies, etc.\n"
                f"• 🔄 Help with **rescheduling** requests\n\n"
                f"What would you like to know?"
            )
        else:
            available = ", ".join(get_all_student_ids())
            response = (
                f"👋 Hello! I'm your **Student Support Assistant**.\n\n"
                f"I can help you with:\n"
                f"• 📊 Attendance information\n"
                f"• 💳 Payment status\n"
                f"• 📅 Class schedule\n"
                f"• 📖 FAQs and general queries\n"
                f"• 🔄 Rescheduling requests\n\n"
                f"To get started, please tell me your **Student ID**.\n"
                f"Available IDs: **{available}**"
            )

        return {
            "response": response,
            "intent": "greeting",
            "sentiment": classification.sentiment,
            "escalated": False,
            "decision_reasoning": "Greeting detected. Responding with welcome message and menu.",
            "classification_details": classification.to_dict(),
        }

    def _handle_farewell(self, classification: IntentClassificationResult) -> dict:
        """Handle farewell / thank you messages."""
        response = (
            "👋 Thank you for chatting with me! Here's a summary:\n\n"
            f"📋 **Session Summary:**\n"
            f"• Messages exchanged: {len(self.conversation_history)}\n"
            f"• Escalations: {len(self.escalation_handler.escalation_log)}\n\n"
            "Have a great day! Feel free to come back anytime. 😊"
        )

        return {
            "response": response,
            "intent": "farewell",
            "sentiment": classification.sentiment,
            "escalated": False,
            "decision_reasoning": "Farewell detected. Providing session summary.",
            "classification_details": classification.to_dict(),
        }

    def _handle_unknown(
        self, query: str, classification: IntentClassificationResult
    ) -> dict:
        """
        Handle unknown queries:
        1. First try to answer using Gemini
        2. If the response seems uncertain, escalate
        """
        return self._handle_with_gemini(query, classification, "unknown")

    def _handle_with_gemini(
        self,
        query: str,
        classification: IntentClassificationResult,
        context_type: str,
    ) -> dict:
        """
        Use Gemini to generate a response for queries that don't match
        specific handlers. Includes guardrails to escalate when needed.
        """
        # Build context for the LLM
        student_context = ""
        if self.student_id:
            summary = self.data_handler.get_student_summary(self.student_id)
            if summary:
                student_context = f"\nCurrent student context: {summary}"

        system_prompt = f"""You are a helpful Student Support Assistant for an online learning academy.
Your role is to help students with their queries about:
- Attendance and classes
- Payment and billing
- Scheduling and bookings
- General academic questions

{student_context}

IMPORTANT RULES:
1. Be helpful, professional, and concise.
2. If you're NOT SURE about the answer, say: "I'm not fully equipped to answer this question. Let me connect you with a human agent."
3. NEVER make up data about the student's attendance, payment, or schedule.
4. Keep responses brief and practical.
5. If the query is completely unrelated to student support (e.g., general knowledge, jokes), politely redirect.

Respond to the following student query:"""

        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=f"{system_prompt}\n\nStudent query: {query}",
                config=genai.types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=500,
                ),
            )

            gemini_response = response.text.strip()

            # Check if Gemini itself suggests escalation
            escalation_phrases = [
                "connect you with a human",
                "escalate",
                "human agent",
                "not equipped",
                "cannot help with",
                "beyond my scope",
            ]

            needs_escalation = any(
                phrase in gemini_response.lower() for phrase in escalation_phrases
            )

            if needs_escalation:
                # Gemini acknowledged it can't help — escalate
                escalation = self.escalation_handler.escalate(
                    reason="unknown_query",
                    student_id=self.student_id,
                    original_query=query,
                )
                return {
                    "response": escalation["message"],
                    "intent": classification.intent,
                    "sentiment": classification.sentiment,
                    "escalated": True,
                    "decision_reasoning": (
                        f"Query classified as '{classification.intent}'. "
                        f"Gemini response indicated it cannot fully address the query. "
                        f"Escalating to human support."
                    ),
                    "classification_details": classification.to_dict(),
                }

            return {
                "response": gemini_response,
                "intent": classification.intent,
                "sentiment": classification.sentiment,
                "escalated": False,
                "decision_reasoning": (
                    f"Query classified as '{context_type}'. "
                    f"No specific handler matched. Used Gemini to generate "
                    f"a contextual response."
                ),
                "classification_details": classification.to_dict(),
            }

        except Exception as e:
            logger.error("Gemini response generation failed: %s", e)
            # If Gemini fails, escalate to human
            escalation = self.escalation_handler.escalate(
                reason="unknown_query",
                student_id=self.student_id,
                original_query=query,
            )
            return {
                "response": (
                    "I apologize, but I'm having trouble processing your request "
                    "right now.\n\n" + escalation["message"]
                ),
                "intent": classification.intent,
                "sentiment": classification.sentiment,
                "escalated": True,
                "decision_reasoning": (
                    f"Gemini API failed ({e}). Escalating to human as fallback."
                ),
                "classification_details": classification.to_dict(),
            }

    def get_conversation_history(self) -> list[dict]:
        """Return conversation history as a list of dicts."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.metadata,
            }
            for msg in self.conversation_history
        ]

    def get_agent_stats(self) -> dict:
        """Return agent session statistics."""
        return {
            "student_id": self.student_id,
            "identified": self.identified,
            "messages": len(self.conversation_history),
            "escalations": self.escalation_handler.get_stats(),
        }
