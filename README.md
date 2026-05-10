# Kubernetes MCP Server

A **Model Context Protocol (MCP) server** that gives AI assistants (like Claude) real-time, read-only access to your Kubernetes cluster — enabling natural-language cluster debugging, monitoring, and inspection without writing a single `kubectl` command.

---

## What Is This?

The **MCP (Model Context Protocol)** is an open standard that lets AI models call external tools in a structured, safe way. This server implements MCP over SSE (Server-Sent Events), exposing Kubernetes cluster data as callable tools.

When connected to an AI assistant, you can ask things like:

- *"Why is my pod crashing in the production namespace?"*
- *"Show me all deployments with fewer ready replicas than desired."*
- *"What events happened on node worker-1 in the last hour?"*
- *"List all secrets in the payments namespace."*

The AI calls the right tools, reads the live cluster state, and gives you a human-readable answer — all without you touching `kubectl`.

---

## Architecture

```
AI Assistant (Claude, etc.)
        │
        │  MCP over SSE (HTTP)
        ▼
┌─────────────────────────┐
│      main.py            │  ← Starlette + uvicorn SSE server
│      server.py          │  ← MCP app, tool registration & dispatch
│      k8s_client.py      │  ← Kubernetes API client init
│                         │
│   tools/                │
│   ├── pods.py           │  get_pods, get_pod_logs, describe_pod
│   ├── nodes.py          │  get_nodes, get_node_logs
│   ├── workloads.py      │  get_deployments
│   ├── networking.py     │  get_services
│   ├── events.py         │  get_events
│   ├── cluster.py        │  get_namespaces, get_resource_usage, get_persistent_volumes
│   └── configs.py        │  get_config_maps, get_secrets
└─────────────────────────┘
        │
        │  Kubernetes Python Client
        ▼
  Kubernetes Cluster (API Server)
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `get_pods` | List pods in a namespace or all namespaces — status, restarts, node, IP |
| `get_pod_logs` | Fetch logs from a pod/container (supports `tail`, `previous`) |
| `describe_pod` | Full pod details: conditions, container states, events |
| `get_nodes` | All nodes with status, kubelet version, CPU/memory capacity |
| `get_node_logs` | Node conditions, addresses, and recent events |
| `get_deployments` | Deployments with desired/ready/available replica counts |
| `get_services` | Services with type, cluster IP, external IP, and ports |
| `get_events` | Recent cluster events sorted by time (great for debugging) |
| `get_namespaces` | All namespaces and their status |
| `get_resource_usage` | Live CPU/memory usage per pod (requires metrics-server) |
| `get_persistent_volumes` | PVs with capacity, access modes, claim, and status |
| `get_config_maps` | ConfigMaps in a namespace (keys only) |
| `get_secrets` | Secrets in a namespace — **names and keys only, never values** |

---

## Project Structure

```
K8s-mcp-server/
├── main.py              # Entry point — SSE server (Starlette + uvicorn)
├── server.py            # MCP app, list_tools & call_tool handlers
├── k8s_client.py        # Kubernetes API client initialization
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
├── k8s-manifest.yaml    # Kubernetes deployment manifests (RBAC + Deployment + Service)
└── tools/
    ├── __init__.py      # Tool aggregator & dispatcher
    ├── pods.py          # Pod tools
    ├── nodes.py         # Node tools
    ├── workloads.py     # Deployment tools
    ├── networking.py    # Service tools
    ├── events.py        # Event tools
    ├── cluster.py       # Namespace, metrics, PV tools
    └── configs.py       # ConfigMap & Secret tools
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A running Kubernetes cluster
- `kubectl` configured locally (for local development)

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the MCP server
python main.py
```

Server starts at `http://0.0.0.0:8080`.

MCP endpoints:
- `GET  /sse`       — SSE stream (AI connects here)
- `POST /messages`  — Message handler

---

## Deploy to Kubernetes

### 1. Build and Push the Image

```bash
docker build -t <your-registry>/k8s-mcp-server:latest .
docker push <your-registry>/k8s-mcp-server:latest
```

### 2. Update the Image in the Manifest

Edit `k8s-manifest.yaml` and set your image:

```yaml
image: <your-registry>/k8s-mcp-server:latest
```

### 3. Apply the Manifests

```bash
kubectl apply -f k8s-manifest.yaml
```

This creates:
- A **ServiceAccount** with a **ClusterRole** granting read-only access to pods, nodes, services, deployments, events, namespaces, configmaps, secrets, PVs, and metrics
- A **Deployment** (1 replica, 128Mi/100m requests)
- A **ClusterIP Service** on port 8080

### 4. Access the Server

```bash
# Port-forward to test locally
kubectl port-forward svc/k8s-mcp-server 8080:8080
```

---

## Connect to Claude Desktop

Add this to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "k8s": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Once connected, Claude can call all the tools above against your live cluster.

---

## Security

- **Read-only**: The RBAC ClusterRole uses only `get`, `list`, `watch` verbs — no write access to the cluster.
- **Secrets safety**: `get_secrets` returns key names only, never secret values.
- **No auth on the MCP endpoint**: The server assumes network-level access control (run inside the cluster or behind a gateway for production use).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp` | MCP server framework |
| `kubernetes` | Official Kubernetes Python client |
| `starlette` | ASGI framework for SSE routing |
| `uvicorn` | ASGI server |
