import json
from mcp.types import Tool, TextContent
from kubernetes import client
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_namespaces",
        description="List all namespaces in the cluster",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_resource_usage",
        description="Get resource usage (CPU/Memory) for pods in a namespace (requires metrics-server)",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query (omit for all namespaces)"}
            }
        }
    ),
    Tool(
        name="get_persistent_volumes",
        description="Get all persistent volumes and their status",
        inputSchema={"type": "object", "properties": {}}
    ),
]


async def _get_namespaces(arguments: dict) -> list[TextContent]:
    namespaces = v1.list_namespace()
    result = [
        {"name": ns.metadata.name, "status": ns.status.phase, "age": str(ns.metadata.creation_timestamp)}
        for ns in namespaces.items
    ]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_resource_usage(arguments: dict) -> list[TextContent]:
    try:
        custom_api = client.CustomObjectsApi()
        namespace = arguments.get("namespace")

        if namespace:
            metrics = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods"
            )
        else:
            metrics = custom_api.list_cluster_custom_object(
                group="metrics.k8s.io", version="v1beta1", plural="pods"
            )

        result = []
        for item in metrics.get("items", []):
            pod_metrics = {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "containers": []
            }
            for container in item.get("containers", []):
                pod_metrics["containers"].append({
                    "name": container["name"],
                    "cpu": container["usage"]["cpu"],
                    "memory": container["usage"]["memory"]
                })
            result.append(pod_metrics)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Metrics not available. Ensure metrics-server is installed. Error: {str(e)}")]


async def _get_persistent_volumes(arguments: dict) -> list[TextContent]:
    pvs = v1.list_persistent_volume()
    result = []
    for pv in pvs.items:
        result.append({
            "name": pv.metadata.name,
            "capacity": pv.spec.capacity.get("storage"),
            "access_modes": pv.spec.access_modes,
            "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
            "status": pv.status.phase,
            "claim": (
                f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}"
                if pv.spec.claim_ref else None
            ),
            "storage_class": pv.spec.storage_class_name
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_namespaces": _get_namespaces,
    "get_resource_usage": _get_resource_usage,
    "get_persistent_volumes": _get_persistent_volumes,
}
