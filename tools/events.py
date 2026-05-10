import json
from mcp.types import Tool, TextContent
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_events",
        description="Get recent events in a namespace or all namespaces (useful for debugging)",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query (omit for all namespaces)"},
                "limit": {"type": "integer", "description": "Number of events to return (default: 50)", "default": 50}
            }
        }
    ),
]


async def _get_events(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace")
    limit = arguments.get("limit", 50)

    events = (
        v1.list_namespaced_event(namespace) if namespace
        else v1.list_event_for_all_namespaces()
    )

    sorted_events = sorted(
        events.items,
        key=lambda x: x.last_timestamp or x.event_time,
        reverse=True
    )[:limit]

    result = []
    for event in sorted_events:
        result.append({
            "namespace": event.metadata.namespace,
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "object": f"{event.involved_object.kind}/{event.involved_object.name}",
            "count": event.count,
            "time": str(event.last_timestamp or event.event_time)
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_events": _get_events,
}
