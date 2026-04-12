from crewai import Agent
from app.llm import get_analyst_llm, get_strategist_llm

_NO_REACT = """You are {role}.
Goal: {goal}
{backstory}

Complete the task given to you. Output your answer directly — no Thought/Action/Observation format needed."""

def create_analyst_agent() -> Agent:
    return Agent(
        role="Customer Complaint Analyst",
        goal="Extract issue category, emotional temperature, key facts, urgency signals, risk flags.",
        backstory="Senior CX analyst at a bank. CALM/FRUSTRATED/ANGRY/THREATENING/CHURN-RISK/PR-RISK scale. Structured output only.",
        llm=get_analyst_llm(),
        verbose=False,
        allow_delegation=False,
        memory=False,
        max_iter=1,
        max_retry_limit=1,
        use_system_prompt=False,
        system_template=_NO_REACT,
    )

def create_strategist_agent() -> Agent:
    return Agent(
        role="Response Strategist",
        goal="Produce routing, SLA, tone guide, complaint-specific draft response, internal note.",
        backstory="Head of customer success at a bank. Tone matches emotional temperature. No generic templates.",
        llm=get_strategist_llm(),
        verbose=False,
        allow_delegation=False,
        memory=False,
        max_iter=1,
        max_retry_limit=1,
        use_system_prompt=False,
        system_template=_NO_REACT,
    )
