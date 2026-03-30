"""
Module 3 — Loan Narrative Builder
crew.py

SPEED STRATEGY:
  CrewAI's sequential process runs Agent1 → Agent2 → Agent3 in order.
  We cannot skip this dependency chain (each needs the previous output).
  
  What we DO to reduce time:
  1. All LLMs pre-loaded at import (zero cold start)
  2. streaming=False (full response in one round-trip vs token streaming)
  3. max_output_tokens tightly set per agent (stops generation sooner)
  4. Trimmed task descriptions (fewer input tokens = faster TTFT)
  5. use_system_prompt=False (no ReAct retry loop)
  6. max_iter=1 (single pass per agent)
  
  Realistic floor: ~45-60s for 3 Gemini API calls on Vertex AI.
  This is the network + inference floor — cannot go below it without
  switching to a faster model or running calls in parallel (not possible
  when each call depends on the previous one).
"""

from crewai import Crew, Process
from app.agents import create_alt_data_analyst, create_narrative_writer, create_risk_reviewer
from app.tasks import create_alt_data_task, create_narrative_task, create_review_task


def run(applicant_data: dict, applicant_name: str,
        loan_purpose: str, loan_amount: str) -> dict:

    analyst  = create_alt_data_analyst()
    writer   = create_narrative_writer()
    reviewer = create_risk_reviewer()

    alt_task       = create_alt_data_task(applicant_data, analyst)
    narrative_task = create_narrative_task(applicant_name, loan_purpose, writer, alt_task)
    review_task    = create_review_task(loan_amount, reviewer, alt_task, narrative_task)

    crew = Crew(
        agents=[analyst, writer, reviewer],
        tasks=[alt_task, narrative_task, review_task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()

    def _raw(t):
        return t.output.raw if t.output else ""

    return {
        "signals":   _raw(alt_task),
        "narrative": _raw(narrative_task),
        "review":    _raw(review_task),
    }
