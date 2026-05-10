import json
from mcp.types import Tool, TextContent
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_nodes",
        description="Get all nodes in the cluster with their status, version, and resources",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_node_logs",
        description="Get events and conditions for a specific node",
        inputSchema={
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Name of the node"}
            },
            "required": ["node_name"]
        }
    ),
]


async def _get_nodes(arguments: dict) -> list[TextContent]:
    nodes = v1.list_node()
    result = []
    for node in nodes.items:
        conditions = {c.type: c.status for c in node.status.conditions}
        result.append({
            "name": node.metadata.name,
            "status": "Ready" if conditions.get("Ready") == "True" else "NotReady",
            "version": node.status.node_info.kubelet_version,
            "os": node.status.node_info.os_image,
            "capacity": {
                "cpu": node.status.capacity.get("cpu"),
                "memory": node.status.capacity.get("memory"),
                "pods": node.status.capacity.get("pods")
            },
            "allocatable": {
                "cpu": node.status.allocatable.get("cpu"),
                "memory": node.status.allocatable.get("memory"),
                "pods": node.status.allocatable.get("pods")
            }
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_node_logs(arguments: dict) -> list[TextContent]:
    node_name = arguments["node_name"]
    node = v1.read_node(node_name)

    result = {
        "name": node.metadata.name,
        "conditions": [],
        "addresses": []
    }

    for condition in node.status.conditions:
        result["conditions"].append({
            "type": condition.type,
            "status": condition.status,
            "reason": condition.reason,
            "message": condition.message,
            "lastTransition": str(condition.last_transition_time)
        })

    for address in node.status.addresses:
        result["addresses"].append({
            "type": address.type,
            "address": address.address
        })

    events = v1.list_event_for_all_namespaces(field_selector=f"involvedObject.name={node_name}")
    result["recent_events"] = []
    for event in events.items[:20]:
        result["recent_events"].append({
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "time": str(event.last_timestamp)
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_nodes": _get_nodes,
    "get_node_logs": _get_node_logs,
}
