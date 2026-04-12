import os
import vertexai
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv

load_dotenv()

vertexai.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "us-central1"),
)

_ANALYST_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_output_tokens=1500,
    streaming=False,
)
_WRITER_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    max_output_tokens=8192,   # fast_crew uses this for ALL 3 steps combined
    streaming=False,
)
_REVIEWER_LLM = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.4,
    max_output_tokens=1500,
    streaming=False,
)

def get_analyst_llm():  return _ANALYST_LLM
def get_writer_llm():   return _WRITER_LLM
def get_reviewer_llm(): return _REVIEWER_LLM
def get_llm(temperature: float = 0.4): return _ANALYST_LLM
