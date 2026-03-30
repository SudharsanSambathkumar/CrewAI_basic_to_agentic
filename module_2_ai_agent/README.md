# Module 2: AI Agent — Complaint Intelligence System

## What This Module Teaches

This module introduces **multi-agent workflows** with the key CrewAI concept: **`context=[task]`**. Two agents work sequentially — the Analyst classifies a complaint, and the Strategist reads that analysis automatically to produce a response strategy.

### CrewAI Concepts Covered

| Concept | Where | What You Learn |
|---------|-------|----------------|
| `context=[task]` | `tasks.py` | Agent 2 receives Agent 1's output automatically |
| Multi-agent `Crew` | `crew.py` | Two agents + two tasks in sequential process |
| Temperature per agent | `llm.py` | Low temp (0.2) for analysis, higher (0.6) for creative strategy |
| `system_template` | `agents.py` | Custom system prompt to bypass ReAct format |
| `use_system_prompt=False` | `agents.py` | Disables CrewAI's built-in ReAct loop |

```python
# The key concept — zero manual passing between agents
strategy_task = Task(
    ...,
    context=[analysis_task]  # Agent 2 reads Agent 1's output automatically
)
```

---

## Use Case

A **Complaint Intelligence System** inspired by complaint tone escalation detection in banking. Given a customer complaint and its channel (Email, WhatsApp, Twitter/X, etc.), the system:

1. **Agent 1 (Analyst)** classifies the complaint:
   - Issue category (Billing / Fraud / Service Failure / Account Access / etc.)
   - Emotional temperature (CALM → FRUSTRATED → ANGRY → THREATENING → CHURN-RISK → PR-RISK)
   - Key facts stated by the customer
   - Urgency signals and risk flags (churn, legal, PR)
   - Missing information needed for resolution

2. **Agent 2 (Strategist)** produces a response plan:
   - Routing decision (Front-line Support / Senior Support / Legal / Fraud Team / etc.)
   - SLA with justification
   - Tone guide matched to emotional temperature
   - Draft opening response (complaint-specific, not generic)
   - Internal escalation note

---

## Architecture

```
Customer Complaint + Channel
         │
         ▼
Agent 1: Complaint Analyst (temp=0.2)
  → Issue Category
  → Emotional Temperature (CALM → PR-RISK)
  → Key Facts, Urgency Signals
  → Risk Flags (Churn / Legal / PR)
  → Missing Information
         │
         │  context=[analysis_task]  ←── CrewAI auto-injects output
         │
         ▼
Agent 2: Response Strategist (temp=0.6)
  → Routing Decision + Reason
  → SLA + Justification
  → Tone Guide (matched to temperature)
  → Draft Opening Response (references actual complaint details)
  → Internal Escalation Note
```

---

## File Structure

```
module_2_ai_agent/
├── app/
│   ├── agents.py          # Analyst + Strategist agents with custom system_template
│   ├── tasks.py           # Analysis task + Strategy task with context=[analysis_task]
│   ├── crew.py            # 2-agent sequential crew
│   ├── llm.py             # Dual-temperature LLM setup (0.2 + 0.6)
│   └── main.py            # CLI with sample complaints and channel selection
├── ui/
│   └── streamlit_app.py   # Side-by-side agent output, sample selector, history
├── Dockerfile
└── requirements.txt
```

---

## Code Walkthrough

### `llm.py` — Dual-Temperature LLMs

Two LLM instances are pre-loaded at import time:
- **Analyst LLM:** `temperature=0.2`, `max_output_tokens=1024` — low creativity, high precision for classification
- **Strategist LLM:** `temperature=0.6`, `max_output_tokens=1500` — moderate creativity for draft responses and tone guides

### `agents.py` — Bypassing ReAct

Both agents use `use_system_prompt=False` and a custom `system_template` that tells the agent to output directly — no Thought/Action/Observation format. Combined with `max_iter=1` and `max_retry_limit=1`, this ensures single-pass execution.

```python
_NO_REACT = """You are {role}.
Goal: {goal}
{backstory}

Complete the task given to you. Output your answer directly — 
no Thought/Action/Observation format needed."""
```

### `tasks.py` — The `context=[task]` Pattern

This is the module's core teaching point. The strategy task references the analysis task:

```python
strategy_task = Task(
    description="...",
    agent=strategist,
    context=[analysis_task],    # ← Agent 2 reads Agent 1's output automatically
)
```

CrewAI handles the plumbing: when the Strategist runs, it receives the Analyst's output as additional context. No manual string concatenation, no shared memory — just `context=[task]`.

### `crew.py` — Sequential Crew

Creates both agents and tasks, wires them into a `Crew` with `Process.sequential`, kicks off, and extracts raw output from each task.

### Streamlit UI — Side-by-Side Output

The UI renders Agent 1 and Agent 2 outputs in parallel columns with color-coded panels. Word-by-word streaming display simulates real-time generation. Session history is maintained so you can compare multiple complaint analyses.

---

## Running

### Environment Variables

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_LOCATION=us-central1
```

### CLI Mode

```bash
cd module_2_ai_agent
pip install -r requirements.txt
python app/main.py
```

You can paste your own complaint or press Enter for a sample. Choose a channel from: Email, WhatsApp, Phone, Twitter/X, Branch Walk-in, Mobile App.

### Streamlit UI

```bash
cd module_2_ai_agent
streamlit run ui/streamlit_app.py
```

### Docker

```bash
cd module_2_ai_agent
docker build -t complaint-intelligence .
docker run -p 8501:8501 \
  -e GCP_PROJECT_ID=your-project \
  complaint-intelligence
```

---

## Sample Complaints Included

| Sample | Temperature | Channel |
|--------|-------------|---------|
| EMI double charge + RBI threat | 🔴 HIGH (THREATENING) | Phone |
| Account frozen, rent due tomorrow, Twitter threat | 🔴 HIGH (PR-RISK) | Twitter/X |
| Small statement discrepancy | 🟢 LOW (CALM) | Email |
| Unauthorized ₹45,000 credit card transaction | 🔴 HIGH (THREATENING) | Mobile App |

---

## Example Output

**Input:** *"I have been charged twice for my EMI this month and nobody is picking up the phone. This is absolutely unacceptable. I am going to file a complaint with RBI if this is not resolved TODAY."*

**Agent 1 — Complaint Analyst:**
```
ISSUE CATEGORY: Billing

EMOTIONAL TEMPERATURE: THREATENING
TEMPERATURE REASONING: Customer uses strong language ("absolutely unacceptable"),
threatens regulatory escalation (RBI), and demands same-day resolution.

KEY FACTS STATED:
- Charged twice for EMI this month
- Unable to reach support by phone
- 8-year customer relationship

URGENCY SIGNALS: Same-day deadline, RBI threat

RISK FLAGS:
- Churn Risk: HIGH — 8-year customer expressing deep frustration
- Legal/Regulatory Risk: HIGH — explicit RBI complaint threat
- PR/Social Media Risk: MEDIUM — no social media mention yet
```

**Agent 2 — Response Strategist:**
```
ROUTING DECISION:
- Assign to: Senior Support + Billing Specialist
- Reason: Dual EMI charge requires billing system investigation;
  RBI threat and 8-year tenure warrant senior handling.

SLA: Response within 2 hours — regulatory threat + high churn risk

RESPONSE TONE GUIDE:
Lead with immediate acknowledgment of the billing error. Match the urgency
without being defensive. Reference their 8-year relationship to signal value.

DRAFT OPENING RESPONSE:
"I'm truly sorry about the duplicate EMI charge — I can see this has been
debited twice and I understand how frustrating that is, especially when you
couldn't get through on the phone. I've flagged this for immediate
investigation and reversal..."
```

---

## Dependencies

```
crewai==0.80.0
google-cloud-aiplatform==1.87.0
langchain-google-vertexai==2.0.7
streamlit==1.41.0
python-dotenv==1.0.1
```

---

## What's Next → Module 3

Module 2 uses `context=[task]` so Agent 2 reads Agent 1. In Module 3, you'll chain context so Agent 3 reads **both** Agent 1 and Agent 2 — `context=[alt_task, narrative_task]`. You'll also learn when 3 separate agents are overkill and a single LLM call (Fast Mode) produces identical output 3–5x faster.
