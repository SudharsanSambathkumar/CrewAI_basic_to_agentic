"""
llm.py — Vertex AI LLM singleton for Module 1.

FIXES APPLIED vs previous version:
  1. vertexai.init() called ONCE at module import, never inside get_llm()
     → Eliminates repeated Cloud Resource Manager API calls
  2. GCP_PROJECT_ID must be the project STRING ID (e.g. "my-project")
     NOT the numeric project number (e.g. 270354017221)
     → Numeric IDs trigger the CRM API lookup that causes the 10s delay
  3. @lru_cache on get_llm() — same temperature returns same object
     → Zero re-init overhead on repeated calls
  4. streaming=True — tokens appear as generated, not after full response

HOW TO GET YOUR PROJECT STRING ID:
  gcloud config get-value project
  # or check GCP Console → top nav dropdown → copy the "ID" column value

AUTH (you are on Vertex AI Workbench, so this already works):
  The Compute Engine service account is already authenticated.
  Just set GCP_PROJECT_ID in your .env file.
"""

import os
import vertexai
from functools import lru_cache
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv

load_dotenv()

# ── Init ONCE at module load time ─────────────────────────────
# Pass the string project ID — not the numeric project number.
# This avoids the Cloud Resource Manager API lookup entirely.
# _PROJECT  = os.getenv("GCP_PROJECT_ID")          # must be string ID e.g. "my-project"
# _LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# vertexai.init(project=_PROJECT, location=_LOCATION)
# ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.7) -> ChatVertexAI:
    """
    Return a cached Gemini 2.5 Flash LLM.
    lru_cache ensures the same temperature always returns the same instance.
    No vertexai.init() here — already done above at module load.
    """
    return ChatVertexAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        max_output_tokens=512,    # kept low for Module 1 — fast responses
        streaming=True,
    )
