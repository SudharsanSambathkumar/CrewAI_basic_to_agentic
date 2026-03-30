"""
Module 1 — Basic CrewAI
crew.py — assemble and run the crew.

verbose=False on the Crew keeps console clean.
Set it to True temporarily if you want to see agent reasoning.
"""

from crewai import Crew, Process
from app.agents import create_explainer_agent
from app.tasks import create_explanation_task


def run(user_input: str, history: list = None) -> str:
    """
    Build and run a 1-agent crew.
    history: current session turns as list of {role, content} dicts.
    Returns the final output string.
    """
    agent = create_explainer_agent()
    task  = create_explanation_task(user_input, agent, history=history)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result)
