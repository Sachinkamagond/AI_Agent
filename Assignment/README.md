# 🎓 Student Support AI Agent

An intelligent Python-based AI Agent that simulates a student support assistant. Built with **Google Gemini API** (`google-genai` SDK) for smart intent classification and natural language understanding, combined with **explicit decision logic** for reliable, predictable routing.

> **Not just a chatbot** — This agent implements a deterministic decision engine with explicit Python rules for routing, escalation, and response generation.

---

## 🏗️ Architecture

```
┌─────────────────┐
│   User Input     │
└────────┬────────┘
         ▼
┌──────────────────────┐
│  Intent Classifier    │  ← Two layers:
│  (Rules + Gemini LLM) │     1. Fast keyword matching
└────────┬─────────────┘     2. AI classification
         ▼
┌──────────────────────┐
│   Decision Engine     │  ← Explicit Python logic
│   (Business Rules)    │     NOT just LLM passthrough
└────────┬─────────────┘
         ▼
    ┌────┴─────┬───────────┬──────────────┐
    ▼          ▼           ▼              ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│ Data   │ │  FAQ   │ │Escalation│ │ Gemini   │
│Handler │ │Handler │ │ Handler  │ │ Response │
└────────┘ └────────┘ └──────────┘ └──────────┘
```

### Key Design Decisions

1. **Two-Layer Intent Classification**
   - **Layer 1:** Rule-based keyword matching (fast, no API cost)
   - **Layer 2:** Gemini LLM classification (for ambiguous queries)
   - This ensures quick responses for obvious intents while leveraging AI for nuanced understanding.

2. **Explicit Decision Engine**
   - The routing logic is **deterministic Python code**, not an LLM prompt.
   - Business rules are clearly defined:
     - Payment issues → **Always escalate** (HIGH priority)
     - Angry users → **Always escalate** (regardless of query topic)
     - Reschedule requests → Acknowledge + Escalate
     - Attendance/schedule queries → Answer from data
     - FAQs → Answer from knowledge base
     - Unknown → Try Gemini → Escalate if uncertain

3. **Sentiment-Aware Escalation**
   - The agent detects angry/frustrated users via regex patterns
   - An angry user asking about attendance still gets their data **plus** an escalation ticket

4. **Transparency**
   - Every decision includes reasoning that explains *why* the agent chose that path
   - Classification method (rule-based vs LLM) is logged

---

## 📁 Project Structure

```
student-support-agent/
├── agent/
│   ├── __init__.py
│   ├── intent_classifier.py   # Two-layer intent classification
│   ├── data_handler.py        # Attendance, payment, schedule queries
│   ├── faq_handler.py         # FAQ knowledge base matching
│   ├── escalation_handler.py  # Escalation logic & ticket management
│   └── agent.py               # 🧠 Main orchestrator + decision engine
├── data/
│   ├── __init__.py
│   └── student_data.py        # Sample student records
├── tests/
│   ├── __init__.py
│   └── test_agent.py          # 40+ unit tests
├── main.py                    # CLI interface
├── app.py                     # Streamlit web UI (for demo)
├── config.py                  # Configuration management
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/student-support-agent.git
cd student-support-agent

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux

# 5. Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_api_key_here
```

---

## 🚀 Running the Agent

### Option 1: CLI Interface
```bash
python main.py
```

The CLI provides a simple text-based interface:
- Select a student ID
- Type queries and see structured responses
- View intent classification and decision reasoning

### Option 2: Streamlit Web UI (Recommended for Demo)
```bash
streamlit run app.py
```

The web UI provides:
- 🎨 Polished chat interface
- 👤 Student profile sidebar
- 🧠 Decision reasoning transparency panel
- ⚡ Quick-action buttons for sample queries
- 📊 Session statistics

---

## 🧪 Running Tests

```bash
# Run all tests (no API key needed)
python -m pytest tests/ -v

# Or with unittest
python -m unittest tests.test_agent -v
```

Tests cover:
- ✅ Data handler (attendance, payment, schedule)
- ✅ FAQ handler (keyword matching)
- ✅ Escalation handler (ticket creation, logging, stats)
- ✅ Student data access functions
- ✅ Rule-based intent classification patterns
- ✅ Edge cases (empty IDs, special characters, all students)

---

## 📋 Sample Interactions

### ✅ Case 1: Attendance Query (Data-driven response)
```
User: "What is my attendance?"
Agent: 📊 Attendance Report for Alice Johnson
       Classes Attended: 8 / 10
       Attendance Percentage: 80.0%
       Status: GOOD
       Great job! Your attendance is on track. Keep it up! 💪

Decision: Attendance query with identified student. Answered from data.
```

### ✅ Case 2: FAQ Query (Static response)
```
User: "How do I book a class?"
Agent: 📖 How to Book a Class
       1. Log in to the Student Portal
       2. Navigate to Courses → Browse Available
       3. Select your desired course and click Enroll Now
       ...

Decision: FAQ match found: 'How do I book a class?' (confidence: 0.87)
```

### 🚨 Case 3: Payment Issue (Escalation)
```
User: "Payment failed"
Agent: 🚨 Escalating to Billing Team
       Your payment issue has been flagged as HIGH PRIORITY
       Ticket ID: ESC-1001
       SLA: 2 hours
       Department: Billing & Payments

Decision: Payment issue detected. Business rule: ALL payment issues
          are escalated to billing team immediately.
```

### 🚨 Case 4: Angry User (Sentiment-based escalation)
```
User: "This is terrible! Nothing works!!!"
Agent: 🤝 Connecting you with a Support Specialist
       I understand your frustration...
       Ticket ID: ESC-1002
       Priority: HIGH
       Department: Student Relations

Decision: User sentiment is ANGRY. Escalating to human agent
          regardless of intent. Priority: HIGH
```

### 🔄 Case 5: Reschedule Request (Acknowledge + Escalate)
```
User: "I want to reschedule my class"
Agent: 📅 Rescheduling Request Noted
       I've forwarded your request to Academic Coordination...
       Expected response: within 4 hours

Decision: Reschedule requests require human coordination.
```

---

## 🧠 Decision Matrix

| Intent | Sentiment | Action | Priority |
|--------|-----------|--------|----------|
| `attendance_query` | neutral/positive | Answer from data | — |
| `attendance_query` | angry | Answer + Escalate | HIGH |
| `payment_issue` | any | **Escalate** | HIGH |
| `payment_status` (failed) | any | Show status + **Escalate** | HIGH |
| `complaint` | any | **Escalate** | HIGH |
| `reschedule_request` | any | Acknowledge + **Escalate** | MEDIUM |
| `booking_query` | any | FAQ response | — |
| `faq` | any | FAQ response | — |
| `greeting` | any | Welcome + menu | — |
| `farewell` | any | Goodbye + summary | — |
| `unknown` | any | Try Gemini → Escalate | LOW |

---

## 🔧 Technical Approach

### Intent Classification (Two-Layer)
1. **Rule-Based Layer**: Regex pattern matching against predefined keyword sets for each intent. Fast, deterministic, no API cost.
2. **LLM Layer (Gemini)**: For ambiguous queries, Gemini classifies the intent with a structured JSON response. Uses low temperature (0.1) for consistency.

### Decision Engine
- **NOT a passthrough to LLM**. The decision logic is explicit Python code.
- Business rules are implemented as a priority-ordered chain of if/else statements.
- Each rule handles a specific intent/sentiment combination.
- Every decision includes human-readable reasoning.

### Escalation System
- Tickets are created with unique IDs, priorities, SLAs, and department routing.
- Escalation log maintains full audit trail.
- Statistics tracking by priority and department.

### Sentiment Detection
- Regex-based anger detection (swear words, exclamation marks, ALL CAPS, explicit escalation requests).
- Gemini provides secondary sentiment analysis during intent classification.
- Angry sentiment can override normal routing (e.g., angry + attendance → escalation + data).

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Google Gemini API SDK (latest) |
| `python-dotenv` | Environment variable management |
| `streamlit` | Web UI framework |

---

## 🎥 Demo Video Structure (2-3 min)

Suggested flow for the demo video:
1. **Show the architecture** (30s) — Explain the two-layer approach
2. **Start the Streamlit UI** (10s)
3. **Select a student** — Show profile loading
4. **Test attendance query** — Show data-driven response
5. **Test FAQ** — "How to book a class?"
6. **Test payment issue** — Show escalation with ticket
7. **Test angry user** — Show sentiment detection + escalation
8. **Show decision reasoning** — Expand the reasoning panel
9. **Show session stats** — Messages and escalations

---

## 📝 License

This project is built as part of an assignment. MIT License.
