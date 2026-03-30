# Module 3: Loan Narrative Builder (Agentic AI)

## Use Case
Inspired by **"Loan story builder"** in BFSI.
Thin-file customers with no CIBIL score are assessed using alternative data.
Three agents build a complete credit narrative and loan recommendation.

## Architecture
```
Alt-Data Input (rent, utility, UPI, employment...)
         │
         ▼
Agent 1: Alt-Data Analyst (temp=0.3)
  → Structured credit signals
  → Repayment capacity estimate
         │  context=[alt_task]
         ▼
Agent 2: Credit Narrative Officer (temp=0.7)
  → 5-section credit memo
         │  context=[alt_task, narrative_task]  ← reads BOTH
         ▼
Agent 3: Risk Reviewer (temp=0.4)
  → Consistency check (narrative vs signals)
  → Risk assessment (LOW/MEDIUM/HIGH)
  → APPROVE / CONDITIONAL / REFER / DECLINE
  → Specific loan parameters (amount, rate, tenure, conditions)
```

## Run
```bash
cd module_3_agentic_ai
cp .env.example .env
pip install -r requirements.txt
python app/main.py          # CLI (pre-filled sample applicant)
streamlit run ui/streamlit_app.py  # UI with form
```
