"""
Module 2 — Complaint Intelligence System
tasks.py — full detailed output format restored.
"""

from crewai import Task


def create_analysis_task(complaint: str, channel: str, analyst) -> Task:
    return Task(
        description=(
            f"Channel: {channel}\n"
            f"Customer complaint: {complaint}\n\n"
            "Extract and output ONLY the following structured analysis:\n\n"
            "ISSUE CATEGORY: [Billing / Fraud / Service Failure / Product Quality / "
            "Account Access / Loan/Credit / Regulatory / Other]\n\n"
            "EMOTIONAL TEMPERATURE: [CALM / FRUSTRATED / ANGRY / THREATENING / "
            "CHURN-RISK / PR-RISK]\n"
            "TEMPERATURE REASONING: [1-2 sentences explaining why you chose this level]\n\n"
            "KEY FACTS STATED:\n"
            "- [specific fact 1]\n"
            "- [specific fact 2]\n"
            "- [more if present]\n\n"
            "URGENCY SIGNALS: [None, or list time-sensitive elements]\n\n"
            "RISK FLAGS:\n"
            "- Churn Risk: [HIGH / MEDIUM / LOW] — [reason]\n"
            "- Legal/Regulatory Risk: [HIGH / MEDIUM / LOW] — [reason]\n"
            "- PR/Social Media Risk: [HIGH / MEDIUM / LOW] — [reason]\n\n"
            "MISSING INFORMATION:\n"
            "- [what's needed for resolution 1]\n"
            "- [what's needed for resolution 2]\n"
            "- [what's needed for resolution 3]\n\n"
            "Be precise. Only extract what is stated or strongly implied."
        ),
        expected_output=(
            "Structured complaint analysis: Issue Category, Emotional Temperature "
            "with reasoning, Key Facts, Urgency Signals, Risk Flags, Missing Information."
        ),
        agent=analyst,
    )


def create_strategy_task(complaint: str, channel: str, strategist, analysis_task: Task) -> Task:
    return Task(
        description=(
            f"You have the complaint analysis in your context.\n"
            f"Original channel: {channel}\n\n"
            "Based on the analysis, produce a complete response strategy:\n\n"
            "ROUTING DECISION:\n"
            "- Assign to: [Front-line Support / Senior Support / Specialist Team / "
            "Legal/Compliance / Executive Escalation / Fraud Team]\n"
            "- Reason: [1-2 sentences why this team]\n\n"
            "SLA: [response within X hours] — [justification based on temperature and risk]\n\n"
            "RESPONSE TONE GUIDE:\n"
            "[2-3 sentences on how to sound and why, specific to the emotional temperature]\n\n"
            "DRAFT OPENING RESPONSE:\n"
            "[Write 3-4 sentences. Reference the specific complaint details. "
            "Acknowledge exact issue, validate emotion, state immediate next step. "
            "No generic templates.]\n\n"
            "INTERNAL ESCALATION NOTE:\n"
            "[2-3 sentences for the internal team — what happened, risk level, "
            "what to prioritise]\n\n"
            "Be specific. Draft response must reference actual complaint details."
        ),
        expected_output=(
            "Response strategy: Routing Decision, SLA, Tone Guide, "
            "Draft Opening Response (complaint-specific), Internal Escalation Note."
        ),
        agent=strategist,
        context=[analysis_task],    # Agent 2 reads Agent 1's output automatically
    )
