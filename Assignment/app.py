"""
Student Support AI Agent — Streamlit Web Interface
====================================================
A polished, interactive web UI for the Student Support Agent.
Designed for demo recording and presentation.

Usage:
    streamlit run app.py
"""

import streamlit as st
import logging
from config import Config
from agent.agent import StudentSupportAgent
from data.student_data import get_all_student_ids, get_student

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Student Support AI Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        color: rgba(255,255,255,0.85);
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }

    /* Chat message styling */
    .chat-user {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }
    .chat-agent {
        background-color: #f3e5f5;
        border-left: 4px solid #7b1fa2;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }

    /* Decision card styling */
    .decision-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #ddd;
    }
    .decision-card h4 {
        color: #333;
        margin: 0 0 8px 0;
    }

    /* Stats card */
    .stat-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border: 1px solid #eee;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    .stat-label {
        color: #666;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Student profile card */
    .profile-card {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }

    /* Hide Streamlit's default header/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: white !important;
    }

    /* Escalation alert */
    .escalation-alert {
        background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ────────────────────────────────────────────
def init_session_state():
    """Initialize Streamlit session state."""
    if "agent" not in st.session_state:
        try:
            Config.validate()
            st.session_state.agent = StudentSupportAgent()
            st.session_state.messages = []
            st.session_state.decision_log = []
            st.session_state.initialized = True
        except ValueError as e:
            st.session_state.initialized = False
            st.session_state.error = str(e)

    if "student_set" not in st.session_state:
        st.session_state.student_set = False


# ─── Sidebar ─────────────────────────────────────────────────────────────────
def render_sidebar():
    """Render the sidebar with student selection and stats."""
    with st.sidebar:
        st.markdown("## 🎓 Student Support Agent")
        st.markdown("---")

        # Student selection
        st.markdown("### 👤 Student Selection")
        student_ids = get_all_student_ids()
        options = ["-- Select Student --"] + student_ids
        selected = st.selectbox(
            "Choose a student:",
            options,
            key="student_select",
            label_visibility="collapsed",
        )

        if selected != "-- Select Student --" and (
            not st.session_state.student_set
            or st.session_state.agent.student_id != selected
        ):
            response = st.session_state.agent.set_student(selected)
            st.session_state.student_set = True
            st.session_state.messages.append(
                {"role": "agent", "content": response, "metadata": {}}
            )

        # Show student profile if selected
        if st.session_state.agent.student_id:
            student = get_student(st.session_state.agent.student_id)
            if student:
                st.markdown("### 📋 Student Profile")
                st.markdown(f"**Name:** {student['name']}")
                st.markdown(f"**ID:** {st.session_state.agent.student_id}")

                att_pct = round((student['attended'] / student['total']) * 100, 1)
                st.markdown(f"**Attendance:** {student['attended']}/{student['total']} ({att_pct}%)")

                payment_emoji = "✅" if student['payments'] == "done" else "❌" if student['payments'] == "failed" else "⏳"
                st.markdown(f"**Payment:** {payment_emoji} {student['payments'].title()}")
                st.markdown(f"**Courses:** {', '.join(student['enrolled_courses'])}")

        st.markdown("---")

        # Session stats
        st.markdown("### 📊 Session Stats")
        stats = st.session_state.agent.get_agent_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", stats["messages"])
        with col2:
            st.metric("Escalations", stats["escalations"]["total"])

        st.markdown("---")

        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        sample_queries = [
            "What is my attendance?",
            "How to book a class?",
            "I want to reschedule my class",
            "Payment failed",
            "What's my schedule?",
        ]
        for sq in sample_queries:
            if st.button(f"💬 {sq}", key=f"btn_{sq}", use_container_width=True):
                st.session_state.pending_query = sq

        st.markdown("---")

        # Decision log toggle
        st.markdown("### 🧠 Agent Transparency")
        st.session_state.show_reasoning = st.toggle(
            "Show decision reasoning",
            value=True,
        )

        # Clear chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.decision_log = []
            st.session_state.agent = StudentSupportAgent(
                student_id=st.session_state.agent.student_id
            )
            st.rerun()


# ─── Main Chat Interface ────────────────────────────────────────────────────
def render_chat():
    """Render the main chat interface."""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Student Support AI Agent</h1>
        <p>Powered by Google Gemini • Intelligent Decision Making • Automatic Escalation</p>
    </div>
    """, unsafe_allow_html=True)

    # Architecture overview (collapsible)
    with st.expander("🏗️ How This Agent Works (Click to expand)"):
        st.markdown("""
        **This agent uses a two-layer decision architecture:**

        1. **Intent Classification** — Uses rule-based matching + Gemini LLM to understand your query
        2. **Decision Engine** — Explicit Python logic (not just AI passthrough) routes your query:
           - 📊 **Data queries** → Answered from student records
           - 📖 **FAQ queries** → Answered from knowledge base
           - 🚨 **Escalation triggers** → Payment issues, angry users, unknown queries
           - 💬 **General queries** → Handled by Gemini with guardrails

        **Escalation happens automatically when:**
        - Payment failure is detected
        - User sentiment is angry/frustrated
        - Query is outside the agent's scope
        - Reschedule requests (needs human coordination)
        """)

    # Chat messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])

                    # Show decision reasoning if enabled
                    if (
                        st.session_state.get("show_reasoning", True)
                        and msg.get("metadata", {}).get("decision_reasoning")
                    ):
                        with st.expander("🧠 Decision Reasoning"):
                            meta = msg["metadata"]
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**Intent:** `{meta.get('intent', 'N/A')}`")
                            with col2:
                                st.markdown(f"**Sentiment:** `{meta.get('sentiment', 'N/A')}`")
                            with col3:
                                escalated = meta.get('escalated', False)
                                st.markdown(f"**Escalated:** {'🚨 Yes' if escalated else '✅ No'}")
                            st.info(f"💡 {meta.get('decision_reasoning', 'N/A')}")

                            # Classification method
                            details = meta.get("classification_details", {})
                            if details:
                                st.markdown(
                                    f"**Classification Method:** `{details.get('method', 'N/A')}` "
                                    f"| **Confidence:** `{details.get('confidence', 'N/A')}`"
                                )


# ─── Process Input ───────────────────────────────────────────────────────────
def process_input(query: str):
    """Process user input and get agent response."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": query, "metadata": {}})

    # Get agent response
    with st.spinner("🤖 Thinking..."):
        result = st.session_state.agent.process_query(query)

    # Add agent response with metadata
    st.session_state.messages.append({
        "role": "agent",
        "content": result["response"],
        "metadata": {
            "intent": result["intent"],
            "sentiment": result["sentiment"],
            "escalated": result["escalated"],
            "decision_reasoning": result["decision_reasoning"],
            "classification_details": result.get("classification_details", {}),
        },
    })

    # Log the decision
    st.session_state.decision_log.append({
        "query": query,
        "intent": result["intent"],
        "escalated": result["escalated"],
        "reasoning": result["decision_reasoning"],
    })


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    """Main Streamlit app."""
    init_session_state()

    if not st.session_state.get("initialized", False):
        st.error(f"⚠️ {st.session_state.get('error', 'Failed to initialize agent')}")
        st.info(
            "Please create a `.env` file in the project root with your Gemini API key:\n\n"
            "```\nGEMINI_API_KEY=your_api_key_here\n```\n\n"
            "Get your API key from: https://aistudio.google.com/apikey"
        )
        return

    render_sidebar()
    render_chat()

    # Handle pending queries from sidebar buttons
    if "pending_query" in st.session_state:
        query = st.session_state.pending_query
        del st.session_state.pending_query
        process_input(query)
        st.rerun()

    # Chat input
    query = st.chat_input("Ask me anything about your classes, attendance, payments...")
    if query:
        process_input(query)
        st.rerun()


if __name__ == "__main__":
    main()
