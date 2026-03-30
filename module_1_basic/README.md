# Module 1: Basic CrewAI — AI/Tech Educator Chatbot

## What This Module Teaches

This is the **foundation module**. It introduces the three core primitives of every CrewAI application — **Agent**, **Task**, and **Crew** — through a conversational chatbot that only discusses AI and technology topics.

### CrewAI Concepts Covered

| Concept | Where | What You Learn |
|---------|-------|----------------|
| `Agent` | `agents.py` | Role, goal, backstory, LLM assignment |
| `Task` | `tasks.py` | Description, expected output, agent binding |
| `Crew` | `crew.py` | Agent + Task assembly, `Process.sequential` |
| Session History | `tasks.py` | Injecting conversation context into task descriptions |
| Topic Guardrails | `tasks.py` | Keyword-based routing (on-topic / off-topic / unclear) |

```python
# The 3 primitives — this is the entire mental model
agent  = Agent(role, goal, backstory, llm)
task   = Task(description, expected_output, agent)
result = Crew(agents=[agent], tasks=[task]).kickoff()
```

---

## Use Case

An **AI and Technology Educator** chatbot that:

- Answers questions about AI, ML, software, data, cloud, and related topics
- Politely redirects off-topic questions (politics, food, sports, etc.)
- Maintains session-level conversation history (resets on restart)
- Responds naturally — short answers for simple questions, longer for complex ones
- Never fabricates facts or invents references

---

## Architecture

```
User Input
    │
    ├── Topic Check (keyword-based)
    │   ├── ON-TOPIC  → Full conversational response
    │   ├── OFF-TOPIC → Polite redirect (1 sentence)
    │   └── UNCLEAR   → Warm greeting / clarification
    │
    ▼
Agent: AI/Tech Educator (temp=0.5)
    │
    ├── Session history injected into task description
    │   (last 6 turns as "User: ... / You: ..." pairs)
    │
    ▼
Crew(agents=[agent], tasks=[task], process=sequential)
    │
    ▼
Response (natural language, no rigid templates)
```

---

## File Structure

```
module_1_basic/
├── app/
│   ├── agents.py          # Single agent definition
│   ├── tasks.py           # Topic-guarded task with history injection
│   ├── crew.py            # Crew assembly and run()
│   ├── llm.py             # Vertex AI LLM singleton with @lru_cache
│   └── main.py            # CLI chat loop
├── ui/
│   └── streamlit_app.py   # Chat UI with word-by-word streaming
├── Dockerfile             # Container deployment
└── requirements.txt       # Python dependencies
```

---

## Code Walkthrough

### `llm.py` — LLM Singleton

The LLM is initialized once at module import time to avoid repeated `vertexai.init()` calls. `@lru_cache` ensures the same temperature always returns the same instance.

Key settings:
- **Model:** `gemini-2.5-flash`
- **Temperature:** `0.5` (lower = less hallucination for factual topics)
- **Max output tokens:** `512` (kept low for fast responses in a chatbot)
- **Streaming:** `True` (tokens appear as generated)

### `agents.py` — The Educator Agent

Defines a single agent with:
- **Role:** AI and Tech Educator
- **Goal:** Natural, helpful conversation about AI/tech; redirect everything else
- **Backstory:** Senior AI engineer who explains clearly, never uses rigid templates, and admits uncertainty

### `tasks.py` — Topic-Guarded Tasks

The most interesting file in this module. It implements a simple keyword-based topic classifier:

1. **`_ON_TOPIC`** keywords: ai, machine learning, python, docker, transformer, etc.
2. **`_OFF_TOPIC`** keywords: politics, recipe, cricket, movie, etc.
3. **`_check_topic()`** returns `"on"`, `"off"`, or `"unclear"`

Based on the classification, the task description changes entirely:
- **On-topic:** "Reply naturally like a knowledgeable friend" with rules about length matching
- **Off-topic:** "Respond with ONE friendly sentence redirecting to AI/tech"
- **Unclear:** "Reply warmly in 1-2 sentences, invite them to ask about AI"

Session history (last 6 turns) is prepended to the task description so the agent has conversational context.

### `crew.py` — Crew Assembly

Minimal: creates the agent, creates the task, assembles the crew, kicks off, and returns the string result. This is the pattern you'll see in every module.

---

## Running

### Prerequisites

```bash
# GCP authentication (pick one)
gcloud auth application-default login          # local dev
# OR use Vertex AI Workbench (pre-authenticated)
# OR use a service account on Cloud Run
```

### Environment Variables

```bash
export GCP_PROJECT_ID=your-project-id    # String ID, NOT numeric
export GCP_LOCATION=us-central1          # Optional, defaults to us-central1
```

### CLI Mode

```bash
cd module_1_basic
pip install -r requirements.txt
python app/main.py
```

Commands during chat:
- `clear` — reset session history
- `exit` — quit

### Streamlit UI

```bash
cd module_1_basic
streamlit run ui/streamlit_app.py
```

### Docker

```bash
cd module_1_basic
docker build -t basic-crewai .
docker run -p 8501:8501 \
  -e GCP_PROJECT_ID=your-project \
  basic-crewai
```

---

## Example Interactions

**On-topic (simple):**
```
You: What is RAG?
Agent: RAG — Retrieval Augmented Generation — is a pattern where you give an LLM
access to external documents at query time. Instead of relying purely on what
the model memorized during training, you retrieve relevant chunks from a vector
database and include them in the prompt. This dramatically reduces hallucination
for domain-specific questions.
```

**On-topic (complex):**
```
You: How does attention work in transformers?
Agent: [3-4 paragraphs explaining Q/K/V, scaled dot-product, multi-head attention]
```

**Off-topic:**
```
You: What's a good recipe for pasta?
Agent: That's a bit outside my lane — I focus on AI and tech. Anything on that
front I can help with?
```

**Unclear/greeting:**
```
You: Hey
Agent: Hey! I'm here to chat about AI and technology. What's on your mind?
```

---

## Dependencies

```
crewai==0.80.0
google-cloud-aiplatform
langchain-google-vertexai==2.0.7
streamlit==1.41.0
python-dotenv==1.0.1
```

---

## What's Next → Module 2

Module 1 uses **1 agent, 1 task**. In Module 2, you'll add a **second agent** and learn how `context=[task]` lets Agent 2 automatically receive Agent 1's output — the foundation of multi-agent workflows.
