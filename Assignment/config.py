"""
Configuration management for Student Support AI Agent.
Loads environment variables and provides centralized config.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration for the agent."""

    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Agent Configuration
    MAX_CONVERSATION_HISTORY: int = 20
    ESCALATION_SENTIMENT_THRESHOLD: float = 0.7

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please set it in your .env file or environment variables.\n"
                "Get your API key from: https://aistudio.google.com/apikey"
            )
        return True
