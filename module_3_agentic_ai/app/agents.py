from crewai import Agent
from app.llm import get_analyst_llm, get_writer_llm, get_reviewer_llm

def create_alt_data_analyst() -> Agent:
    return Agent(
        role="Alternative Data Credit Analyst",
        goal="Extract structured creditworthiness signals from alt-data. Flag every missing point.",
        backstory="Specialist credit analyst. Forensic. Structured output only. Never invent data.",
        llm=get_analyst_llm(),
        verbose=False,
        allow_delegation=False,
        memory=False,
        max_iter=1,
        max_retry_limit=1,
        use_system_prompt=False,
    )

def create_narrative_writer() -> Agent:
    return Agent(
        role="Credit Narrative Officer",
        goal="Write a 5-section credit memo in officer voice. Evidence-based. No fabrication.",
        backstory="Senior credit officer. Every claim references actual data from the analysis.",
        llm=get_writer_llm(),
        verbose=False,
        allow_delegation=False,
        memory=False,
        max_iter=1,
        max_retry_limit=1,
        use_system_prompt=False,
    )

def create_risk_reviewer() -> Agent:
    return Agent(
        role="Credit Risk Reviewer",
        goal="Review signals and narrative. Output APPROVE/CONDITIONAL/REFER/DECLINE with exact loan parameters.",
        backstory="Chief credit risk officer, 15 years BFSI. Every recommendation has a specific number.",
        llm=get_reviewer_llm(),
        verbose=False,
        allow_delegation=False,
        memory=False,
        max_iter=1,
        max_retry_limit=1,
        use_system_prompt=False,
    )
