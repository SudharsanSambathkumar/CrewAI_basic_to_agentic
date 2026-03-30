"""
Module 2 — Complaint Intelligence System
crew.py — proper CrewAI Crew with Agent + Task + Process.sequential.
"""

from crewai import Crew, Process
from app.agents import create_analyst_agent, create_strategist_agent
from app.tasks import create_analysis_task, create_strategy_task


def run(complaint: str, channel: str = "Email") -> dict:
    analyst    = create_analyst_agent()
    strategist = create_strategist_agent()

    analysis_task = create_analysis_task(complaint, channel, analyst)
    strategy_task = create_strategy_task(complaint, channel, strategist, analysis_task)

    crew = Crew(
        agents=[analyst, strategist],
        tasks=[analysis_task, strategy_task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()

    def _raw(t):
        return t.output.raw if t.output else ""

    return {
        "analysis": _raw(analysis_task),
        "strategy": _raw(strategy_task),
    }
