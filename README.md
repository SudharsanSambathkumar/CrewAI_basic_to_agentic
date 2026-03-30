# CrewAI: From Basic to Agentic AI

A progressive, hands-on learning course that takes you from zero to production-grade multi-agent AI systems using **CrewAI** and **Google Vertex AI (Gemini 2.5 Flash)**. Each module builds on the previous one, introducing new concepts through real-world **BFSI (Banking, Financial Services, and Insurance)** use cases.

---

## Why This Course?

Most CrewAI tutorials stop at "hello world." This course doesn't. Every module solves a **real industry problem** — complaint triage, credit underwriting, Docker infrastructure management — while teaching the framework concepts that make it work. By Module 4, you're building MCP-powered agentic systems that control live infrastructure through natural language.

---

## Course Architecture

```
Module 1                    Module 2                    Module 3                    Module 4
BASIC CREWAI                AI AGENT                    AGENTIC AI                  DOCKER MCP
───────────                 ────────                    ──────────                  ──────────
1 Agent                     2 Agents                    3 Agents                    MCP Server + Agent
1 Task                      2 Tasks                     3 Tasks + Fast Mode         30+ Docker Tools
Session Chat                context=[task]              Chained context             Tool Use + Vertex AI
                                                        2 execution modes

AI Tech Educator            Complaint Intelligence      Loan Narrative Builder      Docker Infrastructure
                            System                                                  Manager

Topic: Fundamentals         Topic: Agent Handoff        Topic: Multi-Agent          Topic: MCP Protocol
                                                        Orchestration               + External Tools
```

---

## Module Overview

| Module | Name | Agents | BFSI Use Case | Key CrewAI Concepts |
|--------|------|--------|---------------|---------------------|
| **1** | [Basic CrewAI](./module_1_basic/) | 1 | AI/Tech Educator Chatbot | Agent, Task, Crew, `Process.sequential`, session history |
| **2** | [AI Agent](./module_2_ai_agent/) | 2 | Complaint Intelligence System | `context=[task]` for agent handoff, emotional temperature analysis |
| **3** | [Agentic AI](./module_3_agentic_ai/) | 3 | Loan Narrative Builder | Chained `context=[]`, multi-agent orchestration, fast mode (1 LLM call vs 3) |
| **4** | [Docker MCP](./module_4_docker_mcp/) | MCP Agent | Docker Infrastructure Manager | Model Context Protocol, 30+ tools, Vertex AI function calling |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini 2.5 Flash via Vertex AI |
| **Agent Framework** | CrewAI 0.80.0 |
| **LLM Integration** | `langchain-google-vertexai` (CrewAI requirement) |
| **Frontend** | Streamlit |
| **MCP** | `mcp` >= 1.5 (Module 4) |
| **Container Runtime** | Docker (Module 4) |
| **Auth** | GCP Application Default Credentials (ADC) |
| **Deployment** | Docker / Cloud Run |

---

## Prerequisites

- **Python 3.10+**
- **GCP Project** with Vertex AI API enabled
- **Authentication** — one of:
  - Vertex AI Workbench (pre-authenticated)
  - `gcloud auth application-default login` (local dev)
  - Service account on Cloud Run
- **Docker** (Module 4 only)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/SudharsanSambathkumar/CrewAI_basic_to_agentic.git
cd CrewAI_basic_to_agentic

# Start with Module 1
cd module_1_basic
pip install -r requirements.txt

# Set your GCP project (string ID, not numeric)
export GCP_PROJECT_ID=your-project-id
export GCP_LOCATION=us-central1

# Run CLI
python app/main.py

# Or run Streamlit UI
streamlit run ui/streamlit_app.py
```

---

## Performance Optimizations Applied Across All Modules

These patterns were discovered through extensive iteration and are baked into every module:

| Optimization | What It Does | Impact |
|-------------|-------------|--------|
| `use_system_prompt=False` | Disables CrewAI's ReAct retry loop | Eliminates 1–2 extra LLM roundtrips |
| `max_iter=1` | Single-pass agent execution | No retry overhead |
| `max_retry_limit=1` | Prevents infinite retry loops | Predictable execution time |
| `streaming=False` | Full response in one API roundtrip | Faster total completion |
| Eager LLM init | LLMs pre-loaded at module import | Zero cold start on first run |
| Tight `max_output_tokens` | Tuned per agent based on measured output | LLM stops generating sooner |
| Trimmed task descriptions | ~40% fewer input tokens | Faster time-to-first-token |

---

## Project Structure

```
CrewAI_basic_to_agentic/
│
├── module_1_basic/                 # 1-agent session chatbot
│   ├── app/
│   │   ├── agents.py              # AI/Tech Educator agent
│   │   ├── tasks.py               # Topic-guarded conversation task
│   │   ├── crew.py                # Crew assembly + run()
│   │   ├── llm.py                 # Vertex AI LLM singleton
│   │   └── main.py                # CLI entrypoint
│   ├── ui/streamlit_app.py        # Chat UI with streaming display
│   ├── Dockerfile
│   └── requirements.txt
│
├── module_2_ai_agent/              # 2-agent complaint system
│   ├── app/
│   │   ├── agents.py              # Analyst + Strategist agents
│   │   ├── tasks.py               # Analysis + Strategy tasks
│   │   ├── crew.py                # Sequential crew with context passing
│   │   ├── llm.py                 # Dual-temperature LLM setup
│   │   └── main.py                # CLI with sample complaints
│   ├── ui/streamlit_app.py        # Side-by-side agent output UI
│   ├── Dockerfile
│   └── requirements.txt
│
├── module_3_agentic_ai/            # 3-agent loan assessment
│   ├── app/
│   │   ├── agents.py              # Analyst + Writer + Reviewer agents
│   │   ├── tasks.py               # Chained context tasks
│   │   ├── crew.py                # Full 3-agent sequential crew
│   │   ├── fast_crew.py           # Single LLM call alternative
│   │   ├── llm.py                 # Triple-temperature LLM setup
│   │   └── main.py                # CLI with mode selection
│   ├── ui/streamlit_app.py        # Tabbed output + sample profiles
│   ├── Dockerfile
│   └── requirements.txt
│
├── module_4_docker_mcp/            # MCP Docker agent
│   ├── server.py                  # MCP server (30+ Docker tools)
│   ├── client.py                  # CLI agent (Vertex AI + MCP)
│   ├── app.py                     # Streamlit UI with rich rendering
│   ├── Dockerfile
│   └── requirements.txt
│
└── README.md                       # This file
```

---

## Learning Path

**Module 1 → 2:** You go from a single agent chatting about AI topics to two agents that hand off work via `context=[task]`. The key insight: Agent 2 automatically receives Agent 1's output without you writing any glue code.

**Module 2 → 3:** You add a third agent and chain context so the Reviewer sees output from *both* the Analyst and the Writer. You also learn when multi-agent overhead isn't worth it (Fast Mode collapses 3 agents into 1 LLM call).

**Module 3 → 4:** You break out of CrewAI entirely and build an MCP server that exposes Docker operations as tools. The LLM decides which tools to call, executes them, and chains results — the same pattern enterprise AI systems use.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | Yes | — | GCP project string ID (not numeric) |
| `GCP_LOCATION` | No | `us-central1` | Vertex AI region |
| `DOCKER_HOST` | Module 4 | — | Docker daemon TCP address |
| `DOCKER_TLS_VERIFY` | Module 4 | `0` | Enable TLS for Docker |
| `DOCKER_CERT_PATH` | Module 4 | — | Path to Docker TLS certs |

---

## Docker Deployment

Every module includes a `Dockerfile` for containerized deployment:

```bash
# Example: Deploy Module 3
cd module_3_agentic_ai
docker build -t loan-narrative-builder .
docker run -p 8501:8501 \
  -e GCP_PROJECT_ID=your-project \
  -e GCP_LOCATION=us-central1 \
  loan-narrative-builder
```

---

## Key Takeaways Per Module

| Module | You Learn | You Build |
|--------|-----------|-----------|
| 1 | CrewAI primitives (Agent → Task → Crew), topic guardrails, session history injection | A chatbot that refuses off-topic questions and remembers context within a session |
| 2 | Agent-to-agent context passing, emotional temperature classification, structured output extraction | A complaint triage system that classifies severity and generates routing + draft responses |
| 3 | Multi-hop context chains, fast mode vs full crew tradeoffs, BFSI credit assessment workflow | A loan underwriting pipeline that analyzes alt-data, writes a credit memo, and produces a risk decision |
| 4 | MCP protocol, tool-use agentic loops, safety guards for destructive operations, natural language → infrastructure | An AI DevOps assistant that manages Docker through conversation |

---

## Author

**Sudharsan Sambathkumar**
AI Engineer

---

## License

This project is for educational and demonstration purposes.
