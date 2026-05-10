import json
from mcp.types import Tool, TextContent
from k8s_client import apps_v1

TOOLS = [
    Tool(
        name="get_deployments",
        description="Get deployments in a namespace or all namespaces",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query (omit for all namespaces)"}
            }
        }
    ),
]


async def _get_deployments(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace")
    deployments = (
        apps_v1.list_namespaced_deployment(namespace) if namespace
        else apps_v1.list_deployment_for_all_namespaces()
    )

    result = []
    for deploy in deployments.items:
        result.append({
            "name": deploy.metadata.name,
            "namespace": deploy.metadata.namespace,
            "replicas": {
                "desired": deploy.spec.replicas,
                "current": deploy.status.replicas,
                "ready": deploy.status.ready_replicas or 0,
                "available": deploy.status.available_replicas or 0
            },
            "age": str(deploy.metadata.creation_timestamp)
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_deployments": _get_deployments,
}
