# Module 2: Complaint Intelligence System

## Use Case
Inspired by **"Complaint tone escalation detector"** in BFSI/e-commerce.
Every incoming complaint is classified by issue type AND emotional temperature,
then routed with a specific response strategy and draft reply.

## Architecture
```
Customer Complaint + Channel
         │
         ▼
Agent 1: Complaint Analyst (temp=0.2)
  → Issue Category
  → Emotional Temperature (CALM→PR-RISK)
  → Key Facts, Risk Flags
         │  context=[analysis_task]
         ▼
Agent 2: Response Strategist (temp=0.6)
  → Routing Decision + SLA
  → Tone Guide
  → Draft Opening Response (complaint-specific)
  → Internal Escalation Note
```

## Run
```bash
cd module_2_ai_agent
cp .env.example .env
pip install -r requirements.txt
python app/main.py          # CLI
streamlit run ui/streamlit_app.py  # UI
```
