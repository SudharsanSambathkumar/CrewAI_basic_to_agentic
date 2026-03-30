#!/usr/bin/env python3
"""
Docker MCP Client — Vertex AI + Gemini 2.5 Flash
Natural language Docker management via MCP tools.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Tuple

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Content,
    Part,
)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ── Config ────────────────────────────────────────────────────────────────────

GCP_PROJECT  = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
MODEL_NAME   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

MAX_TOOL_ROUNDS       = 10
MAX_PARALLEL_TIMEOUT  = 60   # seconds — build can take a while
MAX_RETRIES           = 2

MCP_SERVER_FILE = Path(__file__).parent / "server.py"

DESTRUCTIVE_KEYWORDS = ["remove", "delete", "prune", "force", "rm", "stop"]

SYSTEM_PROMPT = """You are DockerAI, an expert DevOps assistant that manages Docker
infrastructure through MCP tools. You speak natural language and translate
user requests into the right tool calls automatically.

Key behaviours:
1. When a user asks to build an image without providing a Dockerfile, use the
   'description' field in docker_image_build — never ask them to write a Dockerfile.
2. For port mappings, use simple string format like '8080:80' — not JSON objects.
3. For volumes, use simple string format like '/host:/container' — not JSON objects.
4. For environment variables, use 'KEY=VALUE' string format — not JSON objects.
5. Chain multiple tools when needed (e.g. pull then run, build then run).
6. Ask for confirmation only for destructive actions (remove, prune, force stop).
7. If a tool fails, explain why clearly and suggest a fix.
8. Be concise. Use markdown for structure.
9. Never guess Docker state — always use tools to check.
10. Format sizes, timestamps, and port mappings in a human-friendly way.

Examples of natural language → tool mapping:
  "build a python api image called myapp:1.0"
    → docker_image_build(tag="myapp:1.0", description="a Python 3.11 slim API image")
  "run nginx on port 8080"
    → docker_container_run(image="nginx:latest", ports="8080:80", name="nginx")
  "show logs from my api container"
    → docker_container_logs(container="api", tail=100)
"""

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("docker-agent")

# ── Init Vertex AI once ────────────────────────────────────────────────────────

def _init_vertex():
    if not GCP_PROJECT:
        logger.warning(
            "GCP_PROJECT_ID not set — Vertex AI will attempt auto-detection. "
            "Set it explicitly: export GCP_PROJECT_ID=your-project-id"
        )
    vertexai.init(project=GCP_PROJECT or None, location=GCP_LOCATION)
    logger.info("Vertex AI initialised | project=%s | location=%s | model=%s",
                GCP_PROJECT or "auto", GCP_LOCATION, MODEL_NAME)

# ── Safety guard ───────────────────────────────────────────────────────────────

def is_destructive(tool_name: str) -> bool:
    return any(kw in tool_name.lower() for kw in DESTRUCTIVE_KEYWORDS)

# ── Tool execution ─────────────────────────────────────────────────────────────

async def execute_tool_with_retry(
    session: ClientSession,
    call,
) -> Tuple[str, str]:
    tool_name = call.name
    args = dict(call.args or {})
    logger.info("Calling tool: %s | args=%s", tool_name, args)

    for attempt in range(MAX_RETRIES + 1):
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, args),
                timeout=MAX_PARALLEL_TIMEOUT,
            )
            result_text = "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            ) or "(no output)"
            logger.info("Tool success: %s", tool_name)
            return tool_name, result_text
        except Exception as e:
            logger.warning("Tool failed: %s | attempt %d | error=%s", tool_name, attempt + 1, e)
            if attempt >= MAX_RETRIES:
                return tool_name, f"ERROR: {e}"
            await asyncio.sleep(1)

# ── Agent loop ─────────────────────────────────────────────────────────────────

async def agent_loop(
    model: GenerativeModel,
    session: ClientSession,
    vertex_tools,
    history: List[Content],
):
    for round_index in range(MAX_TOOL_ROUNDS):
        logger.info("Agent round %d", round_index + 1)

        response  = model.generate_content(contents=history, tools=vertex_tools)
        candidate = response.candidates[0]
        history.append(candidate.content)

        parts      = candidate.content.parts
        tool_calls = []
        text_parts = []

        for part in parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
            if hasattr(part, "function_call") and part.function_call:
                tool_calls.append(part.function_call)

        if text_parts:
            print("\nDockerAI:\n", "".join(text_parts))

        if not tool_calls:
            break

        # Safety check
        for call in tool_calls:
            if is_destructive(call.name):
                confirm = input(f"\n⚠️  Destructive action: {call.name}. Proceed? (yes/no): ")
                if confirm.lower() != "yes":
                    print("Operation cancelled.")
                    return

        # Execute tools (parallel for independent ones)
        results = await asyncio.gather(
            *(execute_tool_with_retry(session, call) for call in tool_calls)
        )

        tool_results = [
            Part.from_function_response(name=name, response={"result": result_text})
            for name, result_text in results
        ]
        history.append(Content(role="user", parts=tool_results))

# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    _init_vertex()

    model = GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT)

    server_params = StdioServerParameters(
        command="python",
        args=[str(MCP_SERVER_FILE)],
    )

    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            await session.initialize()
            logger.info("MCP session initialised")

            tool_list = await session.list_tools()
            function_declarations = [
                FunctionDeclaration(
                    name=t.name,
                    description=t.description or "",
                    parameters=t.inputSchema,
                )
                for t in tool_list.tools
            ]
            vertex_tools = [Tool(function_declarations=function_declarations)]
            logger.info("%d tools loaded", len(function_declarations))

            history: List[Content] = []

            print("\n🐳 Docker MCP Agent Ready")
            print(f"   Model: {MODEL_NAME}  |  Project: {GCP_PROJECT or 'auto-detect'}")
            print("   Type naturally — e.g. 'pull nginx and run it on port 8080'")
            print("   Type 'exit' to quit.\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n👋 Bye!")
                    break

                if user_input.lower() in ("exit", "quit"):
                    break
                if not user_input:
                    continue

                history.append(Content(role="user", parts=[Part.from_text(user_input)]))

                try:
                    await agent_loop(model, session, vertex_tools, history)
                except Exception as e:
                    logger.error("Agent error: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
