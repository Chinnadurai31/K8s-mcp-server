import json
from mcp.types import Tool, TextContent
from kubernetes.client.rest import ApiException
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_pods",
        description="Get pods in a namespace or all namespaces. Returns pod names, status, restarts, and age.",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace to query (omit for all namespaces)"
                }
            }
        }
    ),
    Tool(
        name="get_pod_logs",
        description="Get logs from a specific pod container",
        inputSchema={
            "type": "object",
            "properties": {
                "pod_name": {"type": "string", "description": "Name of the pod"},
                "namespace": {"type": "string", "description": "Namespace of the pod", "default": "default"},
                "container": {"type": "string", "description": "Container name (optional for single-container pods)"},
                "tail": {"type": "integer", "description": "Number of lines from the end of logs (default: 100)", "default": 100},
                "previous": {"type": "boolean", "description": "Get logs from previous container instance (for crashed pods)", "default": False}
            },
            "required": ["pod_name", "namespace"]
        }
    ),
    Tool(
        name="describe_pod",
        description="Get detailed information about a specific pod including status, conditions, and events",
        inputSchema={
            "type": "object",
            "properties": {
                "pod_name": {"type": "string", "description": "Name of the pod"},
                "namespace": {"type": "string", "description": "Namespace of the pod", "default": "default"}
            },
            "required": ["pod_name", "namespace"]
        }
    ),
]


async def _get_pods(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace")
    pods = v1.list_namespaced_pod(namespace) if namespace else v1.list_pod_for_all_namespaces()

    result = []
    for pod in pods.items:
        container_statuses = pod.status.container_statuses or []
        restarts = sum(cs.restart_count for cs in container_statuses)
        status = pod.status.phase

        if container_statuses:
            for cs in container_statuses:
                if cs.state.waiting:
                    status = f"Waiting: {cs.state.waiting.reason}"
                elif cs.state.terminated:
                    status = f"Terminated: {cs.state.terminated.reason}"

        result.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": status,
            "restarts": restarts,
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip,
            "age": str(pod.metadata.creation_timestamp)
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_pod_logs(arguments: dict) -> list[TextContent]:
    pod_name = arguments["pod_name"]
    namespace = arguments.get("namespace", "default")
    container = arguments.get("container")
    tail = arguments.get("tail", 100)
    previous = arguments.get("previous", False)

    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail,
            previous=previous
        )
        return [TextContent(type="text", text=f"Logs for {pod_name} in {namespace}:\n\n{logs}")]
    except ApiException as e:
        if e.status == 404:
            return [TextContent(type="text", text=f"Pod {pod_name} not found in namespace {namespace}")]
        raise


async def _describe_pod(arguments: dict) -> list[TextContent]:
    pod_name = arguments["pod_name"]
    namespace = arguments.get("namespace", "default")

    pod = v1.read_namespaced_pod(pod_name, namespace)

    result = {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "labels": pod.metadata.labels,
        "annotations": pod.metadata.annotations,
        "status": {
            "phase": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status, "reason": c.reason, "message": c.message}
                for c in (pod.status.conditions or [])
            ],
            "host_ip": pod.status.host_ip,
            "pod_ip": pod.status.pod_ip,
            "start_time": str(pod.status.start_time)
        },
        "containers": []
    }

    for container in pod.spec.containers:
        result["containers"].append({
            "name": container.name,
            "image": container.image,
            "ports": [{"containerPort": p.container_port, "protocol": p.protocol} for p in (container.ports or [])]
        })

    if pod.status.container_statuses:
        result["container_statuses"] = []
        for cs in pod.status.container_statuses:
            status_info = {
                "name": cs.name,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "image": cs.image
            }
            if cs.state.running:
                status_info["state"] = "Running"
                status_info["started_at"] = str(cs.state.running.started_at)
            elif cs.state.waiting:
                status_info["state"] = "Waiting"
                status_info["reason"] = cs.state.waiting.reason
                status_info["message"] = cs.state.waiting.message
            elif cs.state.terminated:
                status_info["state"] = "Terminated"
                status_info["reason"] = cs.state.terminated.reason
                status_info["exit_code"] = cs.state.terminated.exit_code
            result["container_statuses"].append(status_info)

    events = v1.list_namespaced_event(namespace, field_selector=f"involvedObject.name={pod_name}")
    result["events"] = []
    for event in sorted(events.items, key=lambda x: x.last_timestamp or x.event_time, reverse=True)[:10]:
        result["events"].append({
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "count": event.count,
            "time": str(event.last_timestamp or event.event_time)
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_pods": _get_pods,
    "get_pod_logs": _get_pod_logs,
    "describe_pod": _describe_pod,
}
