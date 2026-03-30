"""
Module 2 — llm.py
Eager init + global instances + streaming=False for speed.
"""

import os
import vertexai
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv

load_dotenv()

# Init once at module load — zero cold start on first run()
vertexai.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "us-central1"),
)

_ANALYST_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.2,
    max_output_tokens=1024,
    streaming=False,
)

_STRATEGIST_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.6,
    max_output_tokens=1500,
    streaming=False,
)

def get_analyst_llm():    return _ANALYST_LLM
def get_strategist_llm(): return _STRATEGIST_LLM
def get_llm(temperature: float = 0.4): return _ANALYST_LLM
