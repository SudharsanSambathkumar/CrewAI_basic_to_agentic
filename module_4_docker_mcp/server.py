#!/usr/bin/env python3
"""
Docker MCP Server — natural language friendly.

Changes from original:
  - docker_image_build: accepts plain English description OR raw Dockerfile.
    If description given, server auto-generates the Dockerfile. User never
    needs to write escaped strings.
  - docker_container_run: ports/volumes/environment accept both JSON objects
    AND simple strings like "8080:80", "/host:/container", "KEY=VALUE".
  - docker_compose_up: accepts plain YAML string (unchanged) but description
    field added so Gemini can generate the compose file from natural language.
  - docker_container_copy_file: dest_path now has clear example in description.
  - All tool descriptions rewritten to be more natural-language friendly.
"""

import asyncio
import base64
import io
import json
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import anyio
import docker
import docker.errors
from docker.models.containers import Container
from docker.models.images import Image
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docker-mcp")

app = Server("docker-mcp-server")

_client: docker.DockerClient | None = None


def get_client() -> docker.DockerClient:
    global _client
    if _client is not None:
        return _client

    docker_host = os.environ.get("DOCKER_HOST", "tcp://localhost:2375").strip()
    if not docker_host:
        raise docker.errors.DockerException(
            "DOCKER_HOST is not set.\n"
            "Set it to your Docker VM: export DOCKER_HOST=tcp://YOUR_VM_IP:2375"
        )

    tls_config: bool | docker.tls.TLSConfig = False
    if os.environ.get("DOCKER_TLS_VERIFY") == "1":
        cert_path = os.environ.get("DOCKER_CERT_PATH", "")
        if not cert_path:
            raise docker.errors.DockerException(
                "DOCKER_TLS_VERIFY=1 requires DOCKER_CERT_PATH to be set."
            )
        tls_config = docker.tls.TLSConfig(
            client_cert=(
                os.path.join(cert_path, "cert.pem"),
                os.path.join(cert_path, "key.pem"),
            ),
            ca_cert=os.path.join(cert_path, "ca.pem"),
            verify=True,
        )

    try:
        _client = docker.DockerClient(base_url=docker_host, tls=tls_config, timeout=10)
        _client.ping()
        logger.info("✅ Connected to Docker daemon at %s", docker_host)
    except Exception as exc:
        _client = None
        raise docker.errors.DockerException(
            f"Cannot reach Docker daemon at '{docker_host}'.\nReason: {exc}"
        ) from exc

    return _client


def _fmt_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _container_info(c: Container) -> dict:
    c.reload()
    ports = c.ports or {}
    return {
        "id": c.short_id,
        "full_id": c.id,
        "name": c.name,
        "status": c.status,
        "image": c.image.tags[0] if c.image.tags else c.image.short_id,
        "created": c.attrs.get("Created", ""),
        "ports": {k: [p["HostPort"] for p in v] if v else [] for k, v in ports.items()},
        "labels": c.labels,
        "restart_policy": c.attrs.get("HostConfig", {}).get("RestartPolicy", {}),
        "networks": list(c.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
    }


def _image_info(img: Image) -> dict:
    return {
        "id": img.short_id,
        "full_id": img.id,
        "tags": img.tags,
        "size": _fmt_size(img.attrs.get("Size", 0)),
        "created": img.attrs.get("Created", ""),
        "architecture": img.attrs.get("Architecture", ""),
        "os": img.attrs.get("Os", ""),
    }


# ── Natural language helpers ───────────────────────────────────────────────────

def _parse_port_bindings(ports_input: Any) -> dict:
    """
    Accept ports in any format:
      - dict:   {"80/tcp": 8080}
      - string: "8080:80" or "8080:80,443:443" (comma-separated for multiple)
      - list:   ["8080:80", "443:443"]
    Returns docker SDK port binding dict.
    """
    if not ports_input:
        return {}
    if isinstance(ports_input, dict):
        return ports_input
    if isinstance(ports_input, str):
        # Split comma-separated ports: "8080:80,443:443"
        ports_input = [p.strip() for p in ports_input.split(",") if p.strip()]
    result = {}
    for p in ports_input:
        p = str(p).strip()
        if ":" in p:
            parts = p.split(":")
            host_port = parts[0].strip()
            container_part = parts[1].strip()
            if "/" not in container_part:
                container_part += "/tcp"
            try:
                result[container_part] = int(host_port)
            except ValueError:
                result[container_part] = host_port
    return result


def _parse_volumes(volumes_input: Any) -> dict:
    """
    Accept volumes in any format:
      - dict:   {"/host": {"bind": "/container", "mode": "rw"}}  (original)
      - string: "/host:/container" or "/host:/container:ro"       (CLI style)
      - list:   ["/host:/container", "/data:/data:ro"]
    """
    if not volumes_input:
        return {}
    if isinstance(volumes_input, dict):
        return volumes_input
    if isinstance(volumes_input, str):
        volumes_input = [volumes_input]
    result = {}
    for v in volumes_input:
        parts = str(v).split(":")
        if len(parts) >= 2:
            host = parts[0]
            container = parts[1]
            mode = parts[2] if len(parts) > 2 else "rw"
            result[host] = {"bind": container, "mode": mode}
    return result


def _parse_environment(env_input: Any) -> dict:
    """
    Accept environment in any format:
      - dict:   {"KEY": "VALUE"}
      - list:   ["KEY=VALUE", ...]
      - string: "KEY=VALUE" or "KEY=VALUE,KEY2=VALUE2" (comma-separated)
    """
    if not env_input:
        return {}
    if isinstance(env_input, dict):
        return env_input
    if isinstance(env_input, str):
        # Split comma-separated: "DEBUG=true,PORT=8080"
        env_input = [e.strip() for e in env_input.split(",") if e.strip()]
    result = {}
    for item in env_input:
        item = str(item).strip()
        if "=" in item:
            k, v = item.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _generate_dockerfile(description: str) -> str:
    """
    Generate a sensible Dockerfile from a plain English description.
    Handles the most common patterns without needing an LLM call.
    For complex descriptions, this is a best-effort fallback.
    """
    desc_lower = description.lower()

    # Detect base image
    if "python" in desc_lower:
        version = "3.11"
        for v in ["3.12", "3.11", "3.10", "3.9"]:
            if v in desc_lower:
                version = v
                break
        base = f"python:{version}-slim"
        run_setup = (
            "RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*\n"
            "ENV PYTHONDONTWRITEBYTECODE=1\n"
            "ENV PYTHONUNBUFFERED=1\n"
        )
        workdir = "WORKDIR /app"
        # detect common frameworks
        if "fastapi" in desc_lower:
            install = "RUN pip install --no-cache-dir fastapi uvicorn"
            cmd = 'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'
            expose = "EXPOSE 8000"
        elif "flask" in desc_lower:
            install = "RUN pip install --no-cache-dir flask"
            cmd = 'CMD ["python", "app.py"]'
            expose = "EXPOSE 5000"
        elif "django" in desc_lower:
            install = "RUN pip install --no-cache-dir django gunicorn"
            cmd = 'CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:8000"]'
            expose = "EXPOSE 8000"
        else:
            install = "RUN pip install --no-cache-dir -r requirements.txt"
            cmd = 'CMD ["python", "app.py"]'
            expose = ""
        return "\n".join(filter(None, [
            f"FROM {base}", run_setup, workdir, install, expose, cmd
        ]))

    elif "node" in desc_lower or "nodejs" in desc_lower or "javascript" in desc_lower:
        version = "20"
        for v in ["21", "20", "18", "16"]:
            if v in desc_lower:
                version = v
                break
        return "\n".join([
            f"FROM node:{version}-slim",
            "WORKDIR /app",
            "COPY package*.json ./",
            "RUN npm ci --only=production",
            "COPY . .",
            "EXPOSE 3000",
            'CMD ["node", "index.js"]',
        ])

    elif "nginx" in desc_lower:
        return "\n".join([
            "FROM nginx:alpine",
            "COPY . /usr/share/nginx/html",
            "EXPOSE 80",
            'CMD ["nginx", "-g", "daemon off;"]',
        ])

    elif "golang" in desc_lower or "go " in desc_lower:
        return "\n".join([
            "FROM golang:1.22-alpine AS builder",
            "WORKDIR /app",
            "COPY go.mod go.sum ./",
            "RUN go mod download",
            "COPY . .",
            "RUN go build -o main .",
            "FROM alpine:latest",
            "COPY --from=builder /app/main /main",
            "EXPOSE 8080",
            'ENTRYPOINT ["/main"]',
        ])

    # Generic fallback
    return "\n".join([
        "FROM ubuntu:22.04",
        "RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*",
        "WORKDIR /app",
        'CMD ["/bin/bash"]',
    ])


# ── Tool definitions ───────────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    # Image tools
    Tool(
        name="docker_image_list",
        description="List all local Docker images with their tags, sizes and metadata.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filter by image name/tag (optional)"}
            },
        },
    ),
    Tool(
        name="docker_image_pull",
        description="Pull a Docker image from a registry. Just say the image name like 'nginx:latest' or 'python:3.11-slim'.",
        inputSchema={
            "type": "object",
            "properties": {
                "image":    {"type": "string", "description": "Image name, e.g. 'nginx:latest' or 'python:3.11'"},
                "registry": {"type": "string", "description": "Custom registry URL (optional, e.g. 'gcr.io/my-project')"},
                "username": {"type": "string"},
                "password": {"type": "string"},
            },
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_image_push",
        description="Push a local Docker image to a registry.",
        inputSchema={
            "type": "object",
            "properties": {
                "image":    {"type": "string", "description": "Image name:tag to push"},
                "registry": {"type": "string"},
                "username": {"type": "string"},
                "password": {"type": "string"},
            },
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_image_build",
        description=(
            "Build a Docker image. You can either:\n"
            "  1. Provide a plain English description (e.g. 'a Python 3.11 FastAPI app') "
            "     and the server will generate the Dockerfile automatically.\n"
            "  2. Provide the actual Dockerfile content if you need exact control.\n"
            "Always provide a tag like 'myapp:1.0'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tag":         {"type": "string",  "description": "Image tag, e.g. 'myapp:1.0' or 'sample-api:latest'"},
                "description": {"type": "string",  "description": "Plain English description of what the image should be, e.g. 'a Python 3.11 slim image with FastAPI and uvicorn'"},
                "dockerfile":  {"type": "string",  "description": "Raw Dockerfile content (optional — use 'description' instead for simplicity)"},
                "build_args":  {"type": "object",  "description": "Build arguments as key-value pairs (optional)"},
                "labels":      {"type": "object"},
            },
            "required": ["tag"],
        },
    ),
    Tool(
        name="docker_image_remove",
        description="Remove a Docker image by name, tag, or ID. Use force=true if the image is in use.",
        inputSchema={
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Image name:tag or ID"},
                "force": {"type": "boolean", "default": False},
                "prune": {"type": "boolean", "default": False, "description": "Also remove dangling images"},
            },
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_image_inspect",
        description="Get detailed metadata about a Docker image (size, layers, entrypoint, exposed ports, etc.).",
        inputSchema={
            "type": "object",
            "properties": {"image": {"type": "string"}},
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_image_tag",
        description="Tag an existing image with a new name/tag. Useful before pushing to a registry.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source image:tag, e.g. 'myapp:1.0'"},
                "target": {"type": "string", "description": "New tag, e.g. 'gcr.io/my-project/myapp:1.0'"},
            },
            "required": ["source", "target"],
        },
    ),
    Tool(
        name="docker_image_history",
        description="Show the build history and layers of a Docker image.",
        inputSchema={
            "type": "object",
            "properties": {"image": {"type": "string"}},
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_image_prune",
        description="Remove dangling (untagged) images to free up disk space. Set all=true to remove ALL unused images.",
        inputSchema={
            "type": "object",
            "properties": {
                "all": {"type": "boolean", "default": False, "description": "Remove all unused images, not just dangling ones"}
            },
        },
    ),
    # Container tools
    Tool(
        name="docker_container_list",
        description="List Docker containers. By default shows only running containers. Set all=true to include stopped ones.",
        inputSchema={
            "type": "object",
            "properties": {
                "all":     {"type": "boolean", "default": False},
                "filters": {"type": "object",  "description": "Optional filters, e.g. {\"status\": \"exited\"}"},
            },
        },
    ),
    Tool(
        name="docker_container_run",
        description=(
            "Create and start a Docker container. Ports, volumes, and environment variables "
            "accept simple string formats:\n"
            "  ports: '8080:80' or ['8080:80', '443:443']\n"
            "  volumes: '/host/path:/container/path' or ['/data:/data:ro']\n"
            "  environment: 'KEY=VALUE' or ['KEY=VALUE', 'DEBUG=true'] or {\"KEY\": \"VALUE\"}"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image":          {"type": "string", "description": "Image name to run, e.g. 'nginx:latest'"},
                "name":           {"type": "string", "description": "Container name (optional)"},
                "command":        {"type": "string", "description": "Command to run inside the container (optional)"},
                "detach":         {"type": "boolean", "default": True, "description": "Run in background (default: true)"},
                "ports": {
                    "type": "string",
                    "description": "Port mappings. Use format 'hostPort:containerPort'. Multiple ports: '8080:80,443:443'. Example: '8080:80'",
                },
                "volumes": {
                    "type": "string",
                    "description": "Volume mounts. Use format '/host/path:/container/path'. Read-only: '/data:/data:ro'. Example: '/tmp:/app/data'",
                },
                "environment": {
                    "type": "string",
                    "description": "Environment variables as comma-separated KEY=VALUE pairs. Example: 'DEBUG=true,PORT=8080,SECRET=abc'",
                },
                "restart_policy": {
                    "type": "string",
                    "enum": ["no", "always", "on-failure", "unless-stopped"],
                    "default": "no",
                },
                "network":    {"type": "string"},
                "remove":     {"type": "boolean", "default": False, "description": "Auto-remove container when it exits"},
                "mem_limit":  {"type": "string",  "description": "Memory limit, e.g. '512m' or '2g'"},
                "cpu_count":  {"type": "integer"},
            },
            "required": ["image"],
        },
    ),
    Tool(
        name="docker_container_stop",
        description="Stop a running container. Provide the container name or ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "timeout":   {"type": "integer", "default": 10},
            },
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_start",
        description="Start a stopped container by name or ID.",
        inputSchema={
            "type": "object",
            "properties": {"container": {"type": "string"}},
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_restart",
        description="Restart a container by name or ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "timeout":   {"type": "integer", "default": 10},
            },
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_remove",
        description="Remove a container. Use force=true to remove a running container without stopping first.",
        inputSchema={
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "force":     {"type": "boolean", "default": False},
                "volumes":   {"type": "boolean", "default": False, "description": "Also remove anonymous volumes"},
            },
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_logs",
        description="Fetch logs from a container. Specify tail count (default 100) or a time filter.",
        inputSchema={
            "type": "object",
            "properties": {
                "container":  {"type": "string"},
                "tail":       {"type": "integer", "default": 100, "description": "Number of lines from the end"},
                "timestamps": {"type": "boolean", "default": False},
                "since":      {"type": "string",  "description": "Show logs since this time, e.g. '1h', '30m', or ISO datetime"},
            },
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_exec",
        description="Run a command inside a running container and return the output.",
        inputSchema={
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "command":   {"type": "string", "description": "Shell command to run, e.g. 'ls /app' or 'python --version'"},
                "workdir":   {"type": "string"},
                "user":      {"type": "string"},
            },
            "required": ["container", "command"],
        },
    ),
    Tool(
        name="docker_container_inspect",
        description="Get detailed metadata and configuration for a container.",
        inputSchema={
            "type": "object",
            "properties": {"container": {"type": "string"}},
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_stats",
        description="Get live resource usage stats (CPU %, memory, network I/O, disk I/O) for a container.",
        inputSchema={
            "type": "object",
            "properties": {"container": {"type": "string"}},
            "required": ["container"],
        },
    ),
    Tool(
        name="docker_container_copy_file",
        description=(
            "Copy a text file into a running container. "
            "Provide the file content as a string and the full path inside the container, "
            "e.g. dest_path='/app/config.json' or dest_path='/etc/nginx/nginx.conf'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "content":   {"type": "string", "description": "Text content to write to the file"},
                "dest_path": {"type": "string", "description": "Full path inside the container, e.g. '/app/config.json'"},
            },
            "required": ["container", "content", "dest_path"],
        },
    ),
    # Network tools
    Tool(
        name="docker_network_list",
        description="List all Docker networks.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="docker_network_create",
        description="Create a Docker network. Driver defaults to 'bridge'.",
        inputSchema={
            "type": "object",
            "properties": {
                "name":     {"type": "string"},
                "driver":   {"type": "string", "default": "bridge"},
                "labels":   {"type": "object"},
                "internal": {"type": "boolean", "default": False},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_network_remove",
        description="Remove a Docker network by name or ID.",
        inputSchema={
            "type": "object",
            "properties": {"network": {"type": "string"}},
            "required": ["network"],
        },
    ),
    Tool(
        name="docker_network_connect",
        description="Connect a running container to a network.",
        inputSchema={
            "type": "object",
            "properties": {
                "network":   {"type": "string"},
                "container": {"type": "string"},
                "aliases":   {"type": "array", "items": {"type": "string"}},
            },
            "required": ["network", "container"],
        },
    ),
    # Volume tools
    Tool(
        name="docker_volume_list",
        description="List all Docker volumes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="docker_volume_create",
        description="Create a Docker volume.",
        inputSchema={
            "type": "object",
            "properties": {
                "name":   {"type": "string"},
                "driver": {"type": "string", "default": "local"},
                "labels": {"type": "object"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="docker_volume_remove",
        description="Remove a Docker volume by name.",
        inputSchema={
            "type": "object",
            "properties": {
                "volume": {"type": "string"},
                "force":  {"type": "boolean", "default": False},
            },
            "required": ["volume"],
        },
    ),
    # System tools
    Tool(
        name="docker_system_info",
        description="Get Docker daemon info: version, container counts, memory, CPUs, storage driver, etc.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="docker_system_prune",
        description="Clean up Docker: removes all stopped containers, dangling images, and unused networks. Set volumes=true to also remove unused volumes.",
        inputSchema={
            "type": "object",
            "properties": {
                "volumes": {"type": "boolean", "default": False}
            },
        },
    ),
    Tool(
        name="docker_system_df",
        description="Show Docker disk usage broken down by images, containers, and volumes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="docker_compose_up",
        description=(
            "Start a multi-container application using docker-compose. "
            "Provide the docker-compose YAML content as a string. "
            "Example: 'version: \"3\"\\nservices:\\n  web:\\n    image: nginx\\n    ports:\\n      - \"8080:80\"'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "compose_yaml":  {"type": "string", "description": "Full docker-compose.yml content as a string"},
                "project_name":  {"type": "string", "description": "Project name (optional, used as container prefix)"},
                "detach":        {"type": "boolean", "default": True},
            },
            "required": ["compose_yaml"],
        },
    ),
]


# ── Tool handler ───────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
    try:
        result = await anyio.to_thread.run_sync(lambda: _dispatch(name, arguments))
        return [TextContent(type="text", text=result)]
    except docker.errors.DockerException as e:
        return [TextContent(type="text", text=f"❌ Docker error: {e}")]
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return [TextContent(type="text", text=f"❌ Error: {e}")]


def _dispatch(name: str, args: dict) -> str:  # noqa: C901
    client = get_client()

    # Images
    if name == "docker_image_list":
        images = client.images.list(name=args.get("name"))
        if not images:
            return "No images found."
        return json.dumps([_image_info(img) for img in images], indent=2)

    if name == "docker_image_pull":
        auth_cfg = None
        if args.get("username"):
            auth_cfg = {"username": args["username"], "password": args.get("password", "")}
        image_name = args["image"]
        if args.get("registry"):
            image_name = f"{args['registry']}/{image_name}"
        lines = []
        for line in client.api.pull(image_name, stream=True, decode=True, auth_config=auth_cfg):
            if "status" in line:
                lines.append(f"{line['status']} {line.get('progress', '')}".strip())
        img = client.images.get(image_name)
        return f"✅ Pulled {image_name}\n" + "\n".join(lines[-10:]) + f"\n\nImage ID: {img.short_id}"

    if name == "docker_image_push":
        auth_cfg = None
        if args.get("username"):
            auth_cfg = {"username": args["username"], "password": args.get("password", "")}
        image_name = args["image"]
        if args.get("registry"):
            image_name = f"{args['registry']}/{image_name}"
        lines = []
        for line in client.api.push(image_name, stream=True, decode=True, auth_config=auth_cfg):
            if "error" in line:
                return f"❌ Push error: {line['error']}"
            if "status" in line:
                lines.append(f"{line['status']} {line.get('progress', '')}".strip())
        return f"✅ Pushed {image_name}\n" + "\n".join(lines[-10:])

    if name == "docker_image_build":
        tag = args["tag"]
        build_args = args.get("build_args", {})
        labels = args.get("labels", {})

        # Determine Dockerfile content
        if args.get("dockerfile"):
            # User provided raw Dockerfile
            dockerfile_content = args["dockerfile"]
            source = "provided Dockerfile"
        elif args.get("description"):
            # Generate Dockerfile from description
            dockerfile_content = _generate_dockerfile(args["description"])
            source = f"auto-generated from description: '{args['description']}'"
            logger.info("Generated Dockerfile:\n%s", dockerfile_content)
        else:
            return "❌ Please provide either 'dockerfile' content or a 'description' of what you want to build."

        # Build tar context in memory
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            encoded = dockerfile_content.encode("utf-8")
            info = tarfile.TarInfo(name="Dockerfile")
            info.size = len(encoded)
            tar.addfile(info, io.BytesIO(encoded))
        tar_buffer.seek(0)

        logs = []
        image_id = None
        for chunk in client.api.build(
            fileobj=tar_buffer,
            custom_context=True,
            tag=tag,
            buildargs=build_args,
            labels=labels,
            decode=True,
        ):
            if "stream" in chunk:
                line = chunk["stream"].strip()
                if line:
                    logs.append(line)
            if "error" in chunk:
                return f"❌ Build error: {chunk['error']}\n\nLogs:\n" + "\n".join(logs)
            if "aux" in chunk:
                image_id = chunk["aux"].get("ID", "")

        result = f"✅ Built image: {tag}\nImage ID: {image_id or 'unknown'}\nSource: {source}\n\nDockerfile used:\n{dockerfile_content}\n\nBuild output:\n"
        return result + "\n".join(logs[-20:])

    if name == "docker_image_remove":
        img = client.images.get(args["image"])
        client.images.remove(args["image"], force=args.get("force", False))
        if args.get("prune"):
            client.images.prune(filters={"dangling": True})
        return f"✅ Removed image {args['image']} (id: {img.short_id})"

    if name == "docker_image_inspect":
        img = client.images.get(args["image"])
        attrs = img.attrs
        info = {
            "id": img.id,
            "tags": img.tags,
            "created": attrs.get("Created"),
            "architecture": attrs.get("Architecture"),
            "os": attrs.get("Os"),
            "size": _fmt_size(attrs.get("Size", 0)),
            "virtual_size": _fmt_size(attrs.get("VirtualSize", 0)),
            "entrypoint": attrs.get("Config", {}).get("Entrypoint"),
            "cmd": attrs.get("Config", {}).get("Cmd"),
            "exposed_ports": list((attrs.get("Config", {}).get("ExposedPorts") or {}).keys()),
            "env": attrs.get("Config", {}).get("Env", []),
            "layers": len(attrs.get("RootFS", {}).get("Layers", [])),
        }
        return json.dumps(info, indent=2)

    if name == "docker_image_tag":
        img = client.images.get(args["source"])
        img.tag(args["target"])
        return f"✅ Tagged {args['source']} → {args['target']}"

    if name == "docker_image_history":
        img = client.images.get(args["image"])
        history = client.api.history(img.id)
        rows = []
        for h in history:
            rows.append({
                "id": h.get("Id", "")[:12],
                "created": datetime.fromtimestamp(h.get("Created", 0)).isoformat() if h.get("Created") else "",
                "created_by": h.get("CreatedBy", "")[:80],
                "size": _fmt_size(h.get("Size", 0)),
                "comment": h.get("Comment", ""),
            })
        return json.dumps(rows, indent=2)

    if name == "docker_image_prune":
        filters = {"dangling": not args.get("all", False)}
        result = client.images.prune(filters=filters)
        reclaimed = _fmt_size(result.get("SpaceReclaimed", 0))
        removed = [img["Deleted"] for img in (result.get("ImagesDeleted") or [])]
        return f"✅ Pruned {len(removed)} image(s), reclaimed {reclaimed}\n" + "\n".join(removed)

    # Containers
    if name == "docker_container_list":
        containers = client.containers.list(
            all=args.get("all", False),
            filters=args.get("filters"),
        )
        if not containers:
            return "No containers found."
        return json.dumps([_container_info(c) for c in containers], indent=2)

    if name == "docker_container_run":
        kwargs: dict[str, Any] = {
            "image":  args["image"],
            "detach": args.get("detach", True),
            "remove": args.get("remove", False),
        }
        if args.get("name"):        kwargs["name"]        = args["name"]
        if args.get("command"):     kwargs["command"]     = args["command"]
        if args.get("network"):     kwargs["network"]     = args["network"]
        if args.get("mem_limit"):   kwargs["mem_limit"]   = args["mem_limit"]
        if args.get("cpu_count"):   kwargs["cpu_count"]   = args["cpu_count"]

        # Accept natural language formats
        if args.get("ports"):
            kwargs["ports"] = _parse_port_bindings(args["ports"])
        if args.get("volumes"):
            kwargs["volumes"] = _parse_volumes(args["volumes"])
        if args.get("environment"):
            kwargs["environment"] = _parse_environment(args["environment"])

        policy = args.get("restart_policy", "no")
        if policy != "no":
            kwargs["restart_policy"] = {"Name": policy}

        result = client.containers.run(**kwargs)
        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")
        return f"✅ Container started\n" + json.dumps(_container_info(result), indent=2)

    if name == "docker_container_stop":
        c = client.containers.get(args["container"])
        c.stop(timeout=args.get("timeout", 10))
        return f"✅ Stopped container {c.name} ({c.short_id})"

    if name == "docker_container_start":
        c = client.containers.get(args["container"])
        c.start()
        return f"✅ Started container {c.name} ({c.short_id})"

    if name == "docker_container_restart":
        c = client.containers.get(args["container"])
        c.restart(timeout=args.get("timeout", 10))
        return f"✅ Restarted container {c.name} ({c.short_id})"

    if name == "docker_container_remove":
        c = client.containers.get(args["container"])
        name_snap = c.name
        id_snap = c.short_id
        c.remove(force=args.get("force", False), v=args.get("volumes", False))
        return f"✅ Removed container {name_snap} ({id_snap})"

    if name == "docker_container_logs":
        c = client.containers.get(args["container"])
        kwargs = {
            "tail": args.get("tail", 100),
            "timestamps": args.get("timestamps", False),
        }
        if args.get("since"):
            kwargs["since"] = args["since"]
        logs = c.logs(**kwargs)
        return logs.decode("utf-8", errors="replace") if isinstance(logs, bytes) else str(logs)

    if name == "docker_container_exec":
        c = client.containers.get(args["container"])
        kwargs = {}
        if args.get("workdir"): kwargs["workdir"] = args["workdir"]
        if args.get("user"):    kwargs["user"]    = args["user"]
        result = c.exec_run(args["command"], **kwargs)
        output = result.output.decode("utf-8", errors="replace") if result.output else ""
        return f"Exit code: {result.exit_code}\n\n{output}"

    if name == "docker_container_inspect":
        c = client.containers.get(args["container"])
        return json.dumps(_container_info(c), indent=2)

    if name == "docker_container_stats":
        c = client.containers.get(args["container"])
        raw = c.stats(stream=False)
        cpu_delta = raw["cpu_stats"]["cpu_usage"]["total_usage"] - raw["precpu_stats"]["cpu_usage"]["total_usage"]
        sys_delta = raw["cpu_stats"].get("system_cpu_usage", 0) - raw["precpu_stats"].get("system_cpu_usage", 0)
        num_cpus  = raw["cpu_stats"].get("online_cpus", 1)
        cpu_pct   = (cpu_delta / sys_delta) * num_cpus * 100.0 if sys_delta > 0 else 0.0
        mem_usage = raw["memory_stats"].get("usage", 0)
        mem_limit = raw["memory_stats"].get("limit", 1)
        mem_pct   = (mem_usage / mem_limit) * 100.0
        net = raw.get("networks", {})
        net_rx = sum(v.get("rx_bytes", 0) for v in net.values())
        net_tx = sum(v.get("tx_bytes", 0) for v in net.values())
        bio = raw.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
        bio_read  = sum(b["value"] for b in bio if b.get("op") == "Read")
        bio_write = sum(b["value"] for b in bio if b.get("op") == "Write")
        return json.dumps({
            "container":       c.name,
            "cpu_percent":     round(cpu_pct, 2),
            "memory_usage":    _fmt_size(mem_usage),
            "memory_limit":    _fmt_size(mem_limit),
            "memory_percent":  round(mem_pct, 2),
            "network_rx":      _fmt_size(net_rx),
            "network_tx":      _fmt_size(net_tx),
            "block_read":      _fmt_size(bio_read),
            "block_write":     _fmt_size(bio_write),
        }, indent=2)

    if name == "docker_container_copy_file":
        c = client.containers.get(args["container"])
        dest_path = args["dest_path"]
        content   = args["content"].encode("utf-8")
        dest_dir  = str(Path(dest_path).parent)
        filename  = Path(dest_path).name
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        tar_buffer.seek(0)
        c.put_archive(dest_dir, tar_buffer)
        return f"✅ Copied file to {dest_path} in container {c.name}"

    # Networks
    if name == "docker_network_list":
        networks = client.networks.list()
        rows = []
        for n in networks:
            rows.append({
                "id":         n.short_id,
                "name":       n.name,
                "driver":     n.attrs.get("Driver"),
                "scope":      n.attrs.get("Scope"),
                "internal":   n.attrs.get("Internal", False),
                "containers": list(n.attrs.get("Containers", {}).keys()),
            })
        return json.dumps(rows, indent=2)

    if name == "docker_network_create":
        net = client.networks.create(
            args["name"],
            driver=args.get("driver", "bridge"),
            labels=args.get("labels"),
            internal=args.get("internal", False),
        )
        return f"✅ Created network {net.name} ({net.short_id})"

    if name == "docker_network_remove":
        net = client.networks.get(args["network"])
        net.remove()
        return f"✅ Removed network {args['network']}"

    if name == "docker_network_connect":
        net = client.networks.get(args["network"])
        aliases = args.get("aliases", [])
        net.connect(args["container"], aliases=aliases if aliases else None)
        return f"✅ Connected {args['container']} to network {args['network']}"

    # Volumes
    if name == "docker_volume_list":
        volumes = client.volumes.list()
        rows = []
        for v in volumes:
            rows.append({
                "name":       v.name,
                "driver":     v.attrs.get("Driver"),
                "mountpoint": v.attrs.get("Mountpoint"),
                "labels":     v.attrs.get("Labels"),
                "created":    v.attrs.get("CreatedAt"),
            })
        return json.dumps(rows, indent=2)

    if name == "docker_volume_create":
        vol = client.volumes.create(
            name=args["name"],
            driver=args.get("driver", "local"),
            labels=args.get("labels"),
        )
        return f"✅ Created volume {vol.name} (mountpoint: {vol.attrs.get('Mountpoint')})"

    if name == "docker_volume_remove":
        vol = client.volumes.get(args["volume"])
        vol.remove(force=args.get("force", False))
        return f"✅ Removed volume {args['volume']}"

    # System
    if name == "docker_system_info":
        info = client.info()
        summary = {
            "docker_version":       info.get("ServerVersion"),
            "api_version":          client.api.api_version,
            "containers":           info.get("Containers"),
            "containers_running":   info.get("ContainersRunning"),
            "images":               info.get("Images"),
            "storage_driver":       info.get("Driver"),
            "memory":               _fmt_size(info.get("MemTotal", 0)),
            "cpus":                 info.get("NCPU"),
            "kernel_version":       info.get("KernelVersion"),
            "operating_system":     info.get("OperatingSystem"),
            "architecture":         info.get("Architecture"),
        }
        return json.dumps(summary, indent=2)

    if name == "docker_system_prune":
        results   = client.containers.prune()
        c_count   = len(results.get("ContainersDeleted") or [])
        images_r  = client.images.prune()
        i_count   = len(images_r.get("ImagesDeleted") or [])
        nets_r    = client.networks.prune()
        n_count   = len(nets_r.get("NetworksDeleted") or [])
        space     = results.get("SpaceReclaimed", 0) + images_r.get("SpaceReclaimed", 0)
        out = (f"✅ System prune complete\n"
               f"Containers removed: {c_count}\n"
               f"Images removed: {i_count}\n"
               f"Networks removed: {n_count}\n"
               f"Space reclaimed: {_fmt_size(space)}")
        if args.get("volumes"):
            vols_r  = client.volumes.prune()
            v_count = len(vols_r.get("VolumesDeleted") or [])
            out += f"\nVolumes removed: {v_count}"
        return out

    if name == "docker_system_df":
        df = client.df()
        lines = ["=== Docker Disk Usage ===\n"]
        lines.append("📦 IMAGES:")
        for img in df.get("Images", []):
            tags = img.get("RepoTags") or ["<none>"]
            lines.append(f"  {tags[0]:<45} {_fmt_size(img.get('Size', 0))}")
        lines.append("\n🐋 CONTAINERS:")
        for c in df.get("Containers", []):
            lines.append(f"  {c.get('Names', ['?'])[0]:<30} {c.get('Status',''):<15} {_fmt_size(c.get('SizeRootFs', 0))}")
        lines.append("\n💾 VOLUMES:")
        for v in df.get("Volumes", []):
            lines.append(f"  {v.get('Name',''):<40} {_fmt_size(v.get('UsageData', {}).get('Size', 0))}")
        return "\n".join(lines)

    if name == "docker_compose_up":
        import subprocess
        compose_yaml = args["compose_yaml"]
        project_name = args.get("project_name", "mcp-compose")
        detach = args.get("detach", True)
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "docker-compose.yml"
            compose_file.write_text(compose_yaml)
            cmd = ["docker", "compose", "-p", project_name, "-f", str(compose_file), "up"]
            if detach:
                cmd.append("-d")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            if result.returncode != 0:
                return f"❌ docker compose failed (exit {result.returncode}):\n{output}"
            return f"✅ docker compose up ({project_name}):\n{output}"

    return f"❌ Unknown tool: {name}"


async def main():
    logger.info("🐳 Docker MCP Server starting...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
