"""
Module 3 — llm.py
Tight max_output_tokens based on actual measured output sizes.
streaming=False, eager init.
"""

import os
import vertexai
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv

load_dotenv()

vertexai.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "us-central1"),
)

# Tight limits based on measured actual output from production runs
_ANALYST_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_output_tokens=700,     # measured: ~600 tokens actual
    streaming=False,
)
_WRITER_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    max_output_tokens=900,     # measured: ~800 tokens actual
    streaming=False,
)
_REVIEWER_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.4,
    max_output_tokens=1000,    # measured: ~900 tokens actual
    streaming=False,
)

def get_analyst_llm():  return _ANALYST_LLM
def get_writer_llm():   return _WRITER_LLM
def get_reviewer_llm(): return _REVIEWER_LLM
def get_llm(temperature: float = 0.4): return _ANALYST_LLM
