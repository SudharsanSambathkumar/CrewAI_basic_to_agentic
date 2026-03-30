"""
Module 3 — Loan Narrative Builder
tasks.py — trimmed input prompts to reduce input tokens (~40% shorter).
Output format preserved exactly — same quality, fewer input tokens.
"""

from crewai import Task


def create_alt_data_task(applicant_data: dict, analyst) -> Task:
    data_block = "\n".join(f"  {k}: {v}" for k, v in applicant_data.items())
    return Task(
        description=(
            f"APPLICANT DATA:\n{data_block}\n\n"
            "Output EXACTLY:\n"
            "INCOME SIGNALS:\n- [bullets]\n\n"
            "PAYMENT BEHAVIOUR:\n- [bullets]\n\n"
            "STABILITY INDICATORS:\n- [bullets]\n\n"
            "DIGITAL FOOTPRINT:\n- [bullets]\n\n"
            "POSITIVE SIGNALS:\n1.\n2.\n3.\n4.\n5.\n\n"
            "RISK SIGNALS:\n1.\n2.\n3.\n4.\n\n"
            "MISSING DATA POINTS:\n- [bullets]\n\n"
            "MONTHLY INCOME ESTIMATE: ₹[range]\n"
            "REPAYMENT CAPACITY: ₹[range]/month\n"
            "BASIS: [1 sentence]\n\n"
            "Use only provided data. Flag every gap."
        ),
        expected_output="Structured alt-data credit signals with income and repayment estimates.",
        agent=analyst,
    )


def create_narrative_task(applicant_name: str, loan_purpose: str,
                           writer, alt_data_task: Task) -> Task:
    return Task(
        description=(
            f"Applicant: {applicant_name} | Purpose: {loan_purpose}\n"
            "Credit signals are in your context.\n\n"
            "Write CREDIT NARRATIVE MEMO — exactly 5 sections:\n\n"
            "1. APPLICANT PROFILE [2-3 sentences]\n"
            "2. INCOME & CASH FLOW STORY [3-4 sentences — cite specific numbers]\n"
            "3. PAYMENT CHARACTER [3-4 sentences — cite specific history]\n"
            "4. LOAN PURPOSE ASSESSMENT [2-3 sentences]\n"
            "5. OFFICER'S ASSESSMENT [2-3 sentences — strongest honest case]\n\n"
            "Every claim must reference actual data. No fabrication."
        ),
        expected_output="5-section credit narrative memo. Evidence-based, officer voice.",
        agent=writer,
        context=[alt_data_task],
    )


def create_review_task(loan_amount: str, reviewer,
                        alt_data_task: Task, narrative_task: Task) -> Task:
    return Task(
        description=(
            f"Requested: {loan_amount}\n"
            "Raw signals AND narrative are in your context.\n\n"
            "Output EXACTLY:\n\n"
            "CONSISTENCY CHECK: [narrative vs signals — overstated claims? missed risks?]\n\n"
            "CREDIT RISK LEVEL: [LOW/MEDIUM/HIGH]\n\n"
            "TOP 3 RISKS:\n1.\n2.\n3.\n\n"
            "TOP 3 MITIGANTS:\n1.\n2.\n3.\n\n"
            "DECISION: [APPROVE/CONDITIONAL APPROVE/REFER/DECLINE]\n\n"
            "LOAN PARAMETERS:\n"
            "- Recommended amount: ₹[figure]\n"
            "- Tenure: [X months]\n"
            "- Interest rate band: [X%-Y% p.a.]\n"
            "- Processing fee: [X%]\n"
            "- Conditions: [numbered list or None]\n\n"
            "ADDITIONAL DATA REQUIRED: [list or None]\n\n"
            "Every recommendation must have a specific number."
        ),
        expected_output="Credit review: risks, mitigants, decision, specific loan parameters.",
        agent=reviewer,
        context=[alt_data_task, narrative_task],
    )
