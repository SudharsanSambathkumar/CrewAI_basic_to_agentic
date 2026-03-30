"""
Module 3 — fast_crew.py

FAST MODE: Single LLM call that simulates all 3 agents in one shot.
Uses the same LLM, same output format, same quality — just 1 API call.

Why this works:
  - Gemini 2.5 Flash can play multiple roles in one prompt
  - We pass all agent personas + tasks in sequence in one message
  - Output is identical to the 3-agent version
  - Time: ~20-30s instead of ~100s

When to use:
  - Streamlit UI (user is waiting, speed matters)
  - Demo/testing

When to use the full crew (crew.py):
  - Teaching how multi-agent context passing works
  - When you need true agent separation (e.g., different models per role)
"""

from app.llm import get_writer_llm  # writer LLM: temp=0.7, good balance


def run(applicant_data: dict, applicant_name: str,
        loan_purpose: str, loan_amount: str) -> dict:
    """
    Single LLM call. Three sections. Same output format as 3-agent version.
    """
    data_block = "\n".join(f"  {k}: {v}" for k, v in applicant_data.items())

    prompt = f"""You are a credit assessment team. Complete all 3 steps below in sequence.
Use only the data provided. Do not fabricate. Be specific with numbers.

APPLICANT: {applicant_name}
LOAN PURPOSE: {loan_purpose}
REQUESTED AMOUNT: {loan_amount}

APPLICANT DATA:
{data_block}

---

STEP 1 — ALT-DATA ANALYST
Extract credit signals. Output EXACTLY:

INCOME SIGNALS:
- [bullets from data]

PAYMENT BEHAVIOUR:
- [bullets from data]

STABILITY INDICATORS:
- [bullets from data]

DIGITAL FOOTPRINT:
- [bullets from data]

POSITIVE SIGNALS:
1.
2.
3.
4.
5.

RISK SIGNALS:
1.
2.
3.
4.

MISSING DATA POINTS:
- [bullets]

MONTHLY INCOME ESTIMATE: ₹[range]
REPAYMENT CAPACITY: ₹[range]/month
BASIS: [1 sentence]

---

STEP 2 — CREDIT NARRATIVE OFFICER
Using Step 1 signals, write a credit memo. Output EXACTLY:

CREDIT NARRATIVE MEMO

1. APPLICANT PROFILE
[2-3 sentences]

2. INCOME & CASH FLOW STORY
[3-4 sentences — cite specific numbers from Step 1]

3. PAYMENT CHARACTER
[3-4 sentences — cite specific payment history]

4. LOAN PURPOSE ASSESSMENT
[2-3 sentences]

5. OFFICER'S ASSESSMENT
[2-3 sentences — strongest honest case]

---

STEP 3 — CREDIT RISK REVIEWER
Using Step 1 signals AND Step 2 narrative, output EXACTLY:

CONSISTENCY CHECK: [narrative vs signals — any overstated claims?]

CREDIT RISK LEVEL: [LOW/MEDIUM/HIGH]

TOP 3 RISKS:
1.
2.
3.

TOP 3 MITIGANTS:
1.
2.
3.

DECISION: [APPROVE / CONDITIONAL APPROVE / REFER / DECLINE]

LOAN PARAMETERS:
- Recommended amount: ₹[figure]
- Tenure: [X months]
- Interest rate band: [X%-Y% p.a.]
- Processing fee: [X%]
- Conditions:
  1.
  2.
  3.

ADDITIONAL DATA REQUIRED:
- [list or None]"""

    llm = get_writer_llm()
    full_output = llm.invoke(prompt).content

    # Split on step separators
    def _extract(text: str, start: str, end: str = None) -> str:
        try:
            s = text.index(start) + len(start)
            if end and end in text[s:]:
                e = text.index(end, s)
                return text[s:e].strip()
            return text[s:].strip()
        except ValueError:
            return text.strip()

    signals   = _extract(full_output, "STEP 1 — ALT-DATA ANALYST", "STEP 2 — CREDIT NARRATIVE OFFICER") if "STEP 1" in full_output else full_output
    narrative = _extract(full_output, "STEP 2 — CREDIT NARRATIVE OFFICER", "STEP 3 — CREDIT RISK REVIEWER") if "STEP 2" in full_output else ""
    review    = _extract(full_output, "STEP 3 — CREDIT RISK REVIEWER") if "STEP 3" in full_output else ""

    # Fallback: if steps not found, return full output in signals
    if not narrative and not review:
        return {"signals": full_output, "narrative": "", "review": ""}

    return {
        "signals":   signals,
        "narrative": narrative,
        "review":    review,
    }
