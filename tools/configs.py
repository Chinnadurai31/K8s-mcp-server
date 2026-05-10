import json
from mcp.types import Tool, TextContent
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_config_maps",
        description="Get ConfigMaps in a namespace",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query", "default": "default"}
            },
            "required": ["namespace"]
        }
    ),
    Tool(
        name="get_secrets",
        description="Get Secrets in a namespace (names only, not values)",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query", "default": "default"}
            },
            "required": ["namespace"]
        }
    ),
]


async def _get_config_maps(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace", "default")
    config_maps = v1.list_namespaced_config_map(namespace)
    result = []
    for cm in config_maps.items:
        result.append({
            "name": cm.metadata.name,
            "namespace": cm.metadata.namespace,
            "data_keys": list(cm.data.keys()) if cm.data else [],
            "age": str(cm.metadata.creation_timestamp)
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_secrets(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace", "default")
    secrets = v1.list_namespaced_secret(namespace)
    result = []
    for secret in secrets.items:
        result.append({
            "name": secret.metadata.name,
            "namespace": secret.metadata.namespace,
            "type": secret.type,
            "data_keys": list(secret.data.keys()) if secret.data else [],
            "age": str(secret.metadata.creation_timestamp)
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_config_maps": _get_config_maps,
    "get_secrets": _get_secrets,
}
