# Module 3: Agentic AI — Loan Narrative Builder

## What This Module Teaches

This is the **capstone multi-agent module**. It introduces **chained context** (Agent 3 reads both Agent 1 and Agent 2), **dual execution modes** (full 3-agent crew vs. single LLM call), and production-grade performance tuning for CrewAI + Vertex AI.

### CrewAI Concepts Covered

| Concept | Where | What You Learn |
|---------|-------|----------------|
| Chained `context=[]` | `tasks.py` | Agent 3 reads output from both Agent 1 AND Agent 2 |
| 3-agent sequential crew | `crew.py` | Full orchestration with dependency chain |
| Fast Mode | `fast_crew.py` | Collapsing 3 agents into 1 LLM call for identical output |
| Per-agent temperature | `llm.py` | 0.3 (analysis) → 0.7 (narrative) → 0.4 (review) |
| Tight token budgets | `llm.py` | `max_output_tokens` tuned to measured actual output |
| Performance ceiling | `crew.py` | Understanding the ~45-60s floor for 3 sequential Gemini calls |

```python
# The chained context pattern — Agent 3 sees EVERYTHING
review_task = Task(
    ...,
    context=[alt_data_task, narrative_task]  # reads BOTH previous agents
)
```

---

## Use Case

A **Loan Narrative Builder** for thin-file (no credit history) applicants in BFSI. Uses alternative data — rent payments, utility bills, UPI transaction history, mobile recharge patterns, employment stability — to assess creditworthiness.

### Three-Agent Pipeline

1. **Agent 1: Alt-Data Analyst** (temp=0.3)
   - Extracts structured credit signals from raw alternative data
   - Produces income signals, payment behaviour, stability indicators, digital footprint
   - Estimates monthly income range and repayment capacity
   - Flags missing data points

2. **Agent 2: Credit Narrative Officer** (temp=0.7)
   - Reads Agent 1's signals via `context=[alt_data_task]`
   - Writes a 5-section credit memo in officer voice
   - Every claim must reference actual data — no fabrication
   - Sections: Applicant Profile, Income & Cash Flow Story, Payment Character, Loan Purpose Assessment, Officer's Assessment

3. **Agent 3: Credit Risk Reviewer** (temp=0.4)
   - Reads BOTH agents via `context=[alt_data_task, narrative_task]`
   - Performs consistency check (narrative vs. raw signals)
   - Assesses credit risk level (LOW/MEDIUM/HIGH)
   - Issues decision: APPROVE / CONDITIONAL APPROVE / REFER / DECLINE
   - Specifies exact loan parameters (amount, tenure, interest rate band, conditions)

---

## Architecture

```
Alt-Data Input (rent, utility, UPI, mobile, employment...)
         │
         ▼
Agent 1: Alt-Data Analyst (temp=0.3)
  → Structured credit signals
  → Income estimate, repayment capacity
  → Missing data flags
         │
         │  context=[alt_task]
         ▼
Agent 2: Credit Narrative Officer (temp=0.7)
  → 5-section credit narrative memo
  → Evidence-based, officer voice
         │
         │  context=[alt_task, narrative_task]  ←── reads BOTH
         ▼
Agent 3: Credit Risk Reviewer (temp=0.4)
  → Consistency check (narrative vs signals)
  → Risk assessment + Decision
  → Specific loan parameters
  → APPROVE / CONDITIONAL / REFER / DECLINE
```

### Dual Execution Modes

| Mode | Agents | API Calls | Time | When to Use |
|------|--------|-----------|------|-------------|
| **Fast** | 1 (simulated 3) | 1 | ~20-30s | Streamlit UI, demos, testing |
| **Full** | 3 (real CrewAI) | 3 | ~90-120s | Teaching multi-agent flow, when agents need different models |

Fast Mode (`fast_crew.py`) packs all three agent personas into a single prompt with `STEP 1 → STEP 2 → STEP 3` markers, then splits the output. Same quality, 3-5x faster.

---

## File Structure

```
module_3_agentic_ai/
├── app/
│   ├── agents.py          # 3 agents: Analyst, Writer, Reviewer
│   ├── tasks.py           # 3 tasks with chained context
│   ├── crew.py            # Full 3-agent sequential crew
│   ├── fast_crew.py       # Single LLM call alternative
│   ├── llm.py             # Triple-temperature LLM setup (0.3 / 0.7 / 0.4)
│   └── main.py            # CLI with mode selection
├── ui/
│   └── streamlit_app.py   # Tabbed output, sample profiles, fast/full toggle
├── Dockerfile
└── requirements.txt
```

---

## Code Walkthrough

### `llm.py` — Triple-Temperature, Tight Token Budgets

Three pre-loaded LLM instances with token budgets tuned to measured output:

| Agent | Temperature | Max Tokens | Measured Actual |
|-------|-------------|------------|-----------------|
| Analyst | 0.3 | 700 | ~600 |
| Writer | 0.7 | 900 | ~800 |
| Reviewer | 0.4 | 1000 | ~900 |

`streaming=False` for all — full response in one API roundtrip is faster than token streaming when you need the complete output before proceeding to the next agent.

### `tasks.py` — Chained Context

The critical pattern. Task descriptions are trimmed (~40% fewer input tokens than v1) but output format is preserved exactly:

```python
# Task 2 reads Task 1
narrative_task = Task(
    ...,
    context=[alt_data_task]
)

# Task 3 reads BOTH Task 1 and Task 2
review_task = Task(
    ...,
    context=[alt_data_task, narrative_task]
)
```

This means the Reviewer can catch inconsistencies — if the Narrative Writer overstates a signal that the Analyst flagged as weak, the Reviewer will call it out in the consistency check.

### `fast_crew.py` — Single-Call Collapse

Instead of 3 separate API calls, Fast Mode sends one prompt that says: "You are a credit assessment team. Complete all 3 steps below in sequence." The output is split on `STEP 1`, `STEP 2`, `STEP 3` markers.

This works because Gemini 2.5 Flash can play multiple roles in one prompt. The output format and quality are identical — the only difference is execution time.

### `crew.py` — Speed Strategy Documentation

The crew.py file documents the performance reality:
- Sequential process means Agent 1 → Agent 2 → Agent 3 in order (no parallelism possible)
- The network + inference floor for 3 Gemini API calls on Vertex AI is ~45-60 seconds
- All optimizations (eager init, streaming=False, tight tokens, trimmed prompts) reduce overhead but can't break the inference floor

### Streamlit UI — Full-Featured Assessment Interface

Features include:
- **Sample profiles:** Pre-filled applicant data (Ravi Kumar — NTC vegetable vendor, Priya Menon — gig worker)
- **Custom input:** Full form for entering alternative data signals
- **Fast/Full toggle:** Switch between 1-call and 3-agent modes
- **Tabbed output:** Signals → Narrative → Review & Decision with color-coded panels
- **Decision coloring:** Green (APPROVE), Yellow (CONDITIONAL), Red (DECLINE)
- **Session history:** Compare multiple assessments

---

## Running

### Environment Variables

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_LOCATION=us-central1
```

### CLI Mode

```bash
cd module_3_agentic_ai
pip install -r requirements.txt
python app/main.py
```

Select mode:
- `1` — Fast Mode (1 LLM call, ~20-30s)
- `2` — Full Mode (3 CrewAI agents, ~90-120s)

### Streamlit UI

```bash
cd module_3_agentic_ai
streamlit run ui/streamlit_app.py
```

### Docker

```bash
cd module_3_agentic_ai
docker build -t loan-narrative-builder .
docker run -p 8501:8501 \
  -e GCP_PROJECT_ID=your-project \
  loan-narrative-builder
```

---

## Sample Applicant Profiles

### Ravi Kumar — NTC Vegetable Vendor
- Self-employed, 6 years same location
- Rent: ₹8,500/month for 4 years, zero missed payments
- UPI: ~40 transactions/month, avg ticket ₹350
- CIBIL: No score (New To Credit)
- Loan: ₹75,000 for a refrigerated cart

### Priya Menon — Gig Worker (Food Delivery)
- Swiggy + Zomato delivery partner, 2.5 years
- Platform earnings: ₹22,000-28,000/month
- UPI: ~80 transactions/month
- 1 delayed rent payment during COVID
- Loan: ₹45,000 for a second-hand two-wheeler

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

## What's Next → Module 4

Modules 1-3 used CrewAI's built-in agent framework. Module 4 breaks out entirely — you build an **MCP (Model Context Protocol) server** that exposes Docker operations as 30+ tools, and an AI agent that decides which tools to call through natural language conversation. This is the pattern enterprise AI systems use for infrastructure automation.
