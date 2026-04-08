"""
Intent Classifier Module
========================
Two-layer intent classification:
  Layer 1: Fast rule-based keyword matching (no API call needed)
  Layer 2: Gemini LLM classification for ambiguous queries

This ensures quick responses for obvious intents while leveraging
AI for nuanced understanding.
"""

import json
import re
import logging
from typing import Optional

from google import genai
from config import Config

logger = logging.getLogger(__name__)


# ─── Intent Definitions ─────────────────────────────────────────────────────

INTENT_TYPES = [
    "attendance_query",     # Questions about attendance
    "payment_issue",        # Payment failure / problems
    "payment_status",       # Checking payment status
    "reschedule_request",   # Wants to reschedule a class
    "booking_query",        # How to book a class
    "schedule_query",       # Questions about class schedule
    "faq",                  # General FAQ
    "greeting",             # Hi / Hello
    "complaint",            # Angry / frustrated user
    "farewell",             # Bye / Thank you
    "unknown",              # Cannot classify
]

SENTIMENT_TYPES = ["positive", "neutral", "negative", "angry"]


# ─── Rule-Based Keyword Patterns ────────────────────────────────────────────
# These patterns catch obvious intents without needing an API call.

KEYWORD_RULES = {
    "attendance_query": [
        r"\battendance\b",
        r"\bhow many classes\b",
        r"\bclasses.*attend",
        r"\battended\b",
        r"\bpresent\b.*\bclass",
        r"\babsent\b",
        r"\bmissed.*class",
    ],
    "payment_issue": [
        r"\bpayment\s*(failed|failure|error|issue|problem|declined|rejected)\b",
        r"\bcannot\s*pay\b",
        r"\bcan'?t\s*pay\b",
        r"\btransaction\s*failed\b",
        r"\bpayment\s*not\s*(going|working)\b",
        r"\brefund\b",
    ],
    "payment_status": [
        r"\bpayment\s*status\b",
        r"\bhave\s*i\s*paid\b",
        r"\bpayment\s*(done|complete|pending)\b",
        r"\bis\s*my\s*payment\b",
        r"\bfee(s)?\s*status\b",
    ],
    "reschedule_request": [
        r"\breschedule\b",
        r"\bchange\s*(my\s*)?(class|schedule|timing)\b",
        r"\bshift\s*(my\s*)?class\b",
        r"\bpostpone\b",
        r"\bcancel\s*(my\s*)?class\b",
    ],
    "booking_query": [
        r"\bbook\s*(a\s*)?class\b",
        r"\bhow\s*to\s*book\b",
        r"\benroll\b",
        r"\bregistration\b",
        r"\bsign\s*up\b",
        r"\bjoin\s*(a\s*)?class\b",
    ],
    "schedule_query": [
        r"\bschedule\b",
        r"\bnext\s*class\b",
        r"\bclass\s*timing\b",
        r"\bwhen\s*(is|are)\s*(my\s*)?(next\s*)?class\b",
        r"\btimetable\b",
    ],
    "greeting": [
        r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|howdy|sup)\b",
        r"^(namaste|hola)\b",
    ],
    "farewell": [
        r"\b(bye|goodbye|see\s*you|thanks|thank\s*you|that'?s\s*all)\b",
    ],
}

# Patterns that indicate angry / frustrated sentiment
# Patterns checked with IGNORECASE
ANGRY_PATTERNS = [
    r"\b(angry|furious|frustrated|annoyed|pissed|terrible|worst|horrible|hate)\b",
    r"\b(not\s*working|waste\s*of\s*time|useless|pathetic|disgusting)\b",
    r"\b(wtf|damn|hell|stupid|idiot|incompetent)\b",
    r"[!]{2,}",          # Multiple exclamation marks
    r"\bwant\s*to\s*(talk|speak)\s*to\s*(a\s*)?(human|person|manager|someone)\b",
    r"\bescalate\b",
    r"\bcomplaint\b",
]

# Patterns checked WITHOUT IGNORECASE (case-sensitive)
ANGRY_PATTERNS_CASE_SENSITIVE = [
    r"[A-Z][A-Z\s]{8,}[A-Z]",  # Extended CAPS (shouting) — at least 10 chars, starts/ends with uppercase
]


class IntentClassificationResult:
    """Structured result from intent classification."""

    def __init__(
        self,
        intent: str,
        confidence: float,
        sentiment: str,
        reasoning: str,
        method: str,  # "rule_based" or "llm"
        entities: Optional[dict] = None,
    ):
        self.intent = intent
        self.confidence = confidence
        self.sentiment = sentiment
        self.reasoning = reasoning
        self.method = method
        self.entities = entities or {}

    def __repr__(self):
        return (
            f"IntentResult(intent={self.intent}, confidence={self.confidence:.2f}, "
            f"sentiment={self.sentiment}, method={self.method})"
        )

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "sentiment": self.sentiment,
            "reasoning": self.reasoning,
            "method": self.method,
            "entities": self.entities,
        }


class IntentClassifier:
    """
    Two-layer intent classifier:
    1. Rule-based keyword matching (fast, no API call)
    2. Gemini LLM classification (for ambiguous queries)
    """

    def __init__(self):
        """Initialize the classifier with Gemini model."""
        Config.validate()
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.GEMINI_MODEL
        logger.info("IntentClassifier initialized with model: %s", Config.GEMINI_MODEL)

    def classify(self, query: str) -> IntentClassificationResult:
        """
        Classify user query intent using two-layer approach.

        Args:
            query: The user's input text

        Returns:
            IntentClassificationResult with intent, confidence, and sentiment
        """
        if not query or not query.strip():
            return IntentClassificationResult(
                intent="unknown",
                confidence=1.0,
                sentiment="neutral",
                reasoning="Empty query received",
                method="rule_based",
            )

        query_clean = query.strip()

        # ── Layer 1: Check for angry sentiment first ──
        is_angry = self._detect_anger(query_clean)

        # ── Layer 2: Rule-based keyword matching ──
        rule_result = self._rule_based_classify(query_clean)

        if rule_result and rule_result.confidence >= 0.8:
            # High confidence rule match — override sentiment if angry
            if is_angry:
                rule_result.sentiment = "angry"
                # If angry and it's a complaint-worthy topic, mark as complaint
                if rule_result.intent not in ("greeting", "farewell"):
                    logger.info(
                        "Angry sentiment detected on '%s' intent, flagging",
                        rule_result.intent,
                    )
            return rule_result

        # ── Layer 3: LLM-based classification ──
        try:
            llm_result = self._llm_classify(query_clean)
            if is_angry and llm_result.sentiment != "angry":
                llm_result.sentiment = "angry"
            return llm_result
        except Exception as e:
            logger.error("LLM classification failed: %s. Falling back to rules.", e)
            # Fallback to rule result if available, otherwise unknown
            if rule_result:
                if is_angry:
                    rule_result.sentiment = "angry"
                return rule_result
            return IntentClassificationResult(
                intent="unknown",
                confidence=0.3,
                sentiment="angry" if is_angry else "neutral",
                reasoning=f"LLM classification failed: {e}. No rule match found.",
                method="fallback",
            )

    def _detect_anger(self, query: str) -> bool:
        """Detect if the user is angry or frustrated using patterns."""
        for pattern in ANGRY_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.debug("Angry pattern matched: %s", pattern)
                return True
        # Case-sensitive patterns (e.g., ALL CAPS detection)
        for pattern in ANGRY_PATTERNS_CASE_SENSITIVE:
            if re.search(pattern, query):
                logger.debug("Angry case-sensitive pattern matched: %s", pattern)
                return True
        return False

    def _rule_based_classify(self, query: str) -> Optional[IntentClassificationResult]:
        """
        Layer 1: Fast rule-based classification using keyword patterns.
        Returns result only if a confident match is found.
        """
        query_lower = query.lower()
        best_intent = None
        best_score = 0

        for intent, patterns in KEYWORD_RULES.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    match_count += 1
            if match_count > best_score:
                best_score = match_count
                best_intent = intent

        if best_intent and best_score > 0:
            confidence = min(0.7 + (best_score * 0.1), 0.95)
            logger.info(
                "Rule-based match: intent=%s, confidence=%.2f, matches=%d",
                best_intent, confidence, best_score,
            )
            return IntentClassificationResult(
                intent=best_intent,
                confidence=confidence,
                sentiment="neutral",
                reasoning=f"Matched {best_score} keyword pattern(s) for '{best_intent}'",
                method="rule_based",
            )

        return None

    def _llm_classify(self, query: str) -> IntentClassificationResult:
        """
        Layer 2: Use Gemini LLM for intelligent intent classification.
        Used when rule-based matching is inconclusive.
        """
        prompt = f"""You are an intent classifier for a **Student Support System**.
Classify the following student query into EXACTLY ONE intent category.

**Intent Categories:**
- attendance_query: Questions about attendance, classes attended, attendance percentage
- payment_issue: Reports of payment failure, payment problems, refund requests
- payment_status: Checking payment status (NOT reporting a problem)
- reschedule_request: Wants to reschedule, cancel, or change class timing
- booking_query: How to book/enroll in a class
- schedule_query: Questions about class schedule, next class timing
- faq: General questions about the platform, policies, how things work
- greeting: Simple greetings (hi, hello, hey)
- complaint: Angry, frustrated, or unhappy user expressing dissatisfaction
- farewell: Goodbye, thanks, end of conversation
- unknown: Cannot be classified into any above category

**Also detect the user's sentiment:**
- positive: Happy, grateful, excited
- neutral: Normal, informational tone
- negative: Slightly unhappy, concerned
- angry: Very frustrated, aggressive, using strong language

**Student Query:** "{query}"

**Respond ONLY with valid JSON (no markdown, no code blocks):**
{{"intent": "category_name", "confidence": 0.85, "sentiment": "neutral", "reasoning": "brief explanation"}}
"""
        logger.debug("Sending query to Gemini for classification: %s", query[:100])

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent classification
                max_output_tokens=200,
            ),
        )

        # Parse the JSON response
        response_text = response.text.strip()
        # Remove potential markdown code blocks
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON: %s", response_text)
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse LLM response: {response_text}")

        # Validate intent
        intent = result.get("intent", "unknown")
        if intent not in INTENT_TYPES:
            logger.warning("LLM returned unknown intent type: %s", intent)
            intent = "unknown"

        # Validate sentiment
        sentiment = result.get("sentiment", "neutral")
        if sentiment not in SENTIMENT_TYPES:
            sentiment = "neutral"

        return IntentClassificationResult(
            intent=intent,
            confidence=float(result.get("confidence", 0.7)),
            sentiment=sentiment,
            reasoning=result.get("reasoning", "Classified by LLM"),
            method="llm",
        )
