# Module 4: Docker MCP — AI-Powered Docker Infrastructure Manager

## What This Module Teaches

This module breaks out of CrewAI entirely and introduces the **Model Context Protocol (MCP)** — the open standard for connecting LLMs to external tools. You build an MCP server that exposes 30+ Docker operations as structured tools, and an AI agent (powered by Gemini 2.5 Flash on Vertex AI) that decides which tools to call based on natural language conversation.

### Concepts Covered

| Concept | Where | What You Learn |
|---------|-------|----------------|
| MCP Server | `server.py` | Exposing operations as structured tools with JSON schemas |
| MCP Client | `client.py` | Connecting to an MCP server, listing tools, calling tools |
| Vertex AI Function Calling | `client.py` | Converting MCP tools to Vertex AI `FunctionDeclaration`s |
| Agentic Tool Loop | `client.py` | Multi-round loop: LLM → tool call → result → LLM → ... |
| Safety Guards | `client.py` | Confirmation prompts for destructive operations |
| Natural Language Parsing | `server.py` | Accepting "8080:80" instead of `{"80/tcp": 8080}` |
| Dockerfile Generation | `server.py` | Auto-generating Dockerfiles from plain English descriptions |
| `google-genai` SDK | `app.py` | Using the new unified Google GenAI SDK with Vertex AI backend |

---

## Use Case

A **Docker Infrastructure Manager** that lets you control Docker through conversation:

```
You: pull nginx and run it on port 8080
DockerAI: [calls docker_image_pull → docker_container_run → returns status]
✅ Pulled nginx:latest
✅ Container started: nginx → 8080:80/tcp

You: show me CPU and memory stats
DockerAI: [calls docker_container_stats → renders metrics]
CPU: 0.15%  |  Memory: 12.4 MB / 2.0 GB  |  Net RX: 1.2 KB

You: build a python 3.11 fastapi image called myapp:1.0
DockerAI: [generates Dockerfile from description → calls docker_image_build]
✅ Built image: myapp:1.0 (auto-generated Dockerfile)
```

---

## Architecture

```
User (CLI or Streamlit)
         │
         ▼
AI Agent (client.py / app.py)
  │  Gemini 2.5 Flash on Vertex AI
  │  System prompt: "You are DockerAI, an expert DevOps assistant"
  │
  │  Agentic Loop (up to 10 rounds):
  │    1. User message → Gemini
  │    2. Gemini returns function_call(s)
  │    3. Execute tool(s) via MCP session
  │    4. Return results to Gemini
  │    5. Gemini produces next response or more tool calls
  │
  │  MCP Protocol (stdio)
  │
  ▼
Docker MCP Server (server.py)
  │  30+ tools organized by category
  │  Natural language input parsing
  │  Dockerfile auto-generation
  │
  ▼
Docker Engine (via docker SDK)
```

### Three Entry Points

| File | Interface | SDK | Use Case |
|------|-----------|-----|----------|
| `client.py` | CLI (terminal) | `vertexai` + `GenerativeModel` | Development, scripting |
| `app.py` | Streamlit web UI | `google-genai` (unified SDK) | Demo, daily use |
| `server.py` | MCP server (stdio) | `mcp` + `docker` | Tool provider (used by both clients) |

---

## File Structure

```
module_4_docker_mcp/
├── server.py              # MCP server: 30+ Docker tools
├── client.py              # CLI agent: Vertex AI + MCP
├── app.py                 # Streamlit UI: google-genai + MCP + rich rendering
├── Dockerfile             # Cloud Run deployment
└── requirements.txt       # Python dependencies
```

---
### Step 1 — Expose the Docker daemon on your VM

SSH into your GCP VM and run:

```bash
# Create the systemd override directory
sudo mkdir -p /etc/systemd/system/docker.service.d

# Write the override to expose Docker on TCP port 2375 (no TLS)
sudo tee /etc/systemd/system/docker.service.d/tcp.conf << 'CONF'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:2375
CONF

# Reload and restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# Verify Docker is listening on TCP
sudo ss -tlnp | grep 2375
```

Expected output:
```
LISTEN  0  128  0.0.0.0:2375  0.0.0.0:*  users:(("dockerd",...))
```

### Step 2 — Open the firewall port on GCP

```bash
gcloud compute firewall-rules create allow-docker-tcp \
  --allow tcp:2375 \
  --source-ranges 0.0.0.0/0 \
  --description "Docker daemon TCP access for MCP agent" \
  --project YOUR_PROJECT_ID
```

> **Security note:** Port 2375 has no TLS — restrict `--source-ranges` to your
> Cloud Run service IP or VPC range in production. Use port 2376 with TLS for
> production deployments.

### Step 3 — Get your VM's external IP

```bash
gcloud compute instances describe YOUR_VM_NAME \
  --zone YOUR_ZONE \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
```

### Step 4 — Set the DOCKER_HOST environment variable

```bash
# Local / Vertex AI Workbench
export DOCKER_HOST=tcp://YOUR_VM_EXTERNAL_IP:2375

# Verify the connection
docker -H tcp://YOUR_VM_EXTERNAL_IP:2375 info
```
## Code Walkthrough

### `server.py` — The MCP Docker Server

The server exposes Docker operations through the MCP protocol. Key design decisions:

**Natural language input parsing:** Instead of requiring Docker SDK-style JSON, the server accepts simple strings:
- Ports: `"8080:80"` or `"8080:80,443:443"` → parsed into Docker port bindings
- Volumes: `"/host:/container"` or `"/host:/container:ro"` → parsed into Docker volume mounts
- Environment: `"KEY=VALUE"` or `"KEY=VALUE,DEBUG=true"` → parsed into environment dict

**Dockerfile auto-generation:** The `docker_image_build` tool accepts either raw Dockerfile content OR a plain English description. If you say `"a Python 3.11 FastAPI app"`, the server generates:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && ...
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Supported description patterns: Python (FastAPI/Flask/Django), Node.js, Nginx, Golang, and a generic Ubuntu fallback.

**Tool categories (30+ tools):**

| Category | Tools | Examples |
|----------|-------|---------|
| Images (9) | list, pull, push, build, remove, inspect, tag, history, prune | `docker_image_build(tag="myapp:1.0", description="python fastapi")` |
| Containers (11) | list, run, stop, start, restart, remove, logs, exec, inspect, stats, copy_file | `docker_container_run(image="nginx", ports="8080:80")` |
| Networks (4) | list, create, remove, connect | `docker_network_create(name="backend")` |
| Volumes (3) | list, create, remove | `docker_volume_create(name="pgdata")` |
| System (4) | info, prune, df, compose_up | `docker_system_prune(volumes=True)` |

### `client.py` — CLI Agent

Uses `vertexai.GenerativeModel` with function calling. Key features:

**Agentic loop:** Up to `MAX_TOOL_ROUNDS=10` iterations. Each round:
1. Send conversation history to Gemini
2. If response contains `function_call` parts, execute them
3. Parallel execution for independent tool calls via `asyncio.gather`
4. Return results as `Part.from_function_response`
5. Repeat until Gemini responds with text only

**Safety guards:** Destructive operations (`remove`, `delete`, `prune`, `force`, `stop`, `rm`) require explicit `yes` confirmation before execution.

**Retry mechanism:** Failed tool calls are retried up to `MAX_RETRIES=2` times with 1-second backoff.

### `app.py` — Streamlit UI

Uses the newer `google-genai` unified SDK (not `vertexai.GenerativeModel`). Features:

**MCP schema conversion:** Converts MCP tool schemas to Gemini `FunctionDeclaration` format using `_json_to_gemini()` recursive converter.

**Rich result rendering:** Tool results are dispatched to specialized renderers:
- Image lists → card layout with tags, size, architecture
- Container lists → status badges, port mappings, network chips
- Stats → progress bars for CPU/memory, metric cards for network/disk I/O
- System info → grid of metric cards
- Logs → formatted code blocks
- Success/error → colored banners

**Threading model:** The agent runs in a background thread, communicating with Streamlit via a `queue.Queue`. Events (thinking, tool_call, tool_result, text, done) drive real-time UI updates.

---

## Running

### Prerequisites

- Docker daemon accessible (local or remote)
- GCP project with Vertex AI API enabled
- Python 3.10+

### Environment Variables

```bash
export GCP_PROJECT_ID=your-project-id        # or GCP_PROJECT / GOOGLE_CLOUD_PROJECT
export GCP_LOCATION=us-central1
export DOCKER_HOST=tcp://your-vm-ip:2375     # remote Docker daemon
# Optional TLS
export DOCKER_TLS_VERIFY=1
export DOCKER_CERT_PATH=/path/to/certs
```

### CLI Agent

```bash
cd module_4_docker_mcp
pip install -r requirements.txt
python client.py
```

### Streamlit UI

```bash
cd module_4_docker_mcp
pip install streamlit "google-genai[vertexai]" mcp anyio httpx docker
streamlit run app.py
```

### Docker (Cloud Run)

```bash
cd module_4_docker_mcp
docker build -t docker-mcp-ui .
docker run -p 8080:8080 \
  -e GCP_PROJECT=your-project \
  -e DOCKER_HOST=tcp://your-vm-ip:2375 \
  docker-mcp-ui

# Or deploy to Cloud Run
gcloud run deploy docker-mcp-ui --source . --region us-central1
```

---

## Example Commands

```
# Image management
list docker images
pull python:3.11-slim
build a python fastapi image called sample-api:latest
show history of nginx:latest

# Container management
run nginx on port 8080
show logs from my api container
exec "python --version" in my-container
show CPU and memory stats for all containers

# Infrastructure
create a docker network called backend
show docker disk usage
prune all stopped containers and dangling images

# Multi-step (agent chains tools automatically)
pull redis:alpine, run it on port 6379 with restart=always
build a node 20 image called frontend:1.0 and run it on port 3000
```

---

## Safety Features

| Feature | Implementation |
|---------|---------------|
| Destructive action confirmation | `is_destructive()` checks tool name for remove/delete/prune/force/stop keywords |
| Execution timeout | `MAX_PARALLEL_TIMEOUT=60s` per tool call |
| Automatic retries | `MAX_RETRIES=2` with 1-second backoff |
| Tool round limit | `MAX_TOOL_ROUNDS=10` prevents infinite loops |
| Error propagation | Failed tools return error messages to Gemini for explanation |

---

## Dependencies

```
mcp >= 1.5
docker >= 7.1
anyio >= 4.7
httpx >= 0.28
```

Additional for Streamlit UI:
```
streamlit
google-genai[vertexai]
```

Additional for CLI agent:
```
google-cloud-aiplatform
vertexai
```

---

## How This Differs from Modules 1-3

| Aspect | Modules 1-3 | Module 4 |
|--------|-------------|----------|
| Framework | CrewAI | MCP + raw Vertex AI |
| Agent definition | `Agent(role, goal, backstory)` | System prompt + tool declarations |
| Tool use | None (LLM-only) | 30+ Docker tools via MCP |
| Execution | `Crew.kickoff()` | Custom agentic loop with function calling |
| Context passing | `context=[task]` | Conversation history + tool results |
| External effects | None (text output only) | Controls live Docker infrastructure |

This module represents the transition from **framework-managed agents** to **protocol-based agentic systems** — the pattern used in production enterprise AI.
