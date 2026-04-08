"""
Student Support AI Agent — CLI Interface
=========================================
Command-line interface for interacting with the agent.
Useful for testing and debugging.

Usage:
    python main.py
"""

import logging
import sys

# Ensure stdout uses UTF-8 encoding so emojis (🎓) don't crash the console on Windows
sys.stdout.reconfigure(encoding='utf-8')

from config import Config
from agent.agent import StudentSupportAgent
from data.student_data import get_all_student_ids

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the welcome banner."""
    print("\n" + "=" * 65)
    print("  🎓  STUDENT SUPPORT AI AGENT  🎓")
    print("  Powered by Google Gemini")
    print("=" * 65)
    print()


def print_response(result: dict):
    """Pretty-print the agent's response."""
    print("\n" + "─" * 50)
    print("🤖 Agent Response:")
    print("─" * 50)
    print(result["response"])
    print()
    print(f"  📌 Intent: {result['intent']}")
    print(f"  😀 Sentiment: {result['sentiment']}")
    print(f"  🚨 Escalated: {'Yes' if result['escalated'] else 'No'}")
    print(f"  💡 Reasoning: {result['decision_reasoning']}")
    print("─" * 50 + "\n")


def select_student(agent: StudentSupportAgent):
    """Prompt user to select a student ID."""
    available = get_all_student_ids()
    print(f"\n📋 Available Student IDs: {', '.join(available)}")
    print("   (You can also skip and identify later)")

    while True:
        student_id = input("\n👤 Enter Student ID (or press Enter to skip): ").strip()
        if not student_id:
            print("   Skipping student identification. You can set it later.\n")
            return
        response = agent.set_student(student_id)
        print(f"\n{response}")
        if agent.identified:
            return


def main():
    """Main CLI loop."""
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)

    print_banner()

    # Initialize the agent
    agent = StudentSupportAgent()

    # Student selection
    select_student(agent)

    print("\n💬 Start chatting! (Type 'quit' to exit, 'stats' for session stats)\n")

    while True:
        try:
            query = input("You: ").strip()

            if not query:
                continue

            # Special commands
            if query.lower() in ("quit", "exit", "q"):
                print("\n👋 Goodbye! Thanks for using Student Support Agent.")
                stats = agent.get_agent_stats()
                print(f"\n📊 Session Stats:")
                print(f"   • Messages: {stats['messages']}")
                print(f"   • Escalations: {stats['escalations']['total']}")
                break

            if query.lower() == "stats":
                stats = agent.get_agent_stats()
                print(f"\n📊 Session Stats:")
                print(f"   • Student: {stats['student_id'] or 'Not identified'}")
                print(f"   • Messages: {stats['messages']}")
                print(f"   • Escalations: {stats['escalations']}")
                continue

            if query.lower().startswith("switch "):
                new_id = query.split(" ", 1)[1].strip()
                response = agent.set_student(new_id)
                print(f"\n{response}\n")
                continue

            # Process the query
            result = agent.process_query(query)
            print_response(result)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error("Error processing query: %s", e, exc_info=True)
            print(f"\n❌ An error occurred: {e}")
            print("   Please try again.\n")


if __name__ == "__main__":
    main()
