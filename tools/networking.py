import json
from mcp.types import Tool, TextContent
from k8s_client import v1

TOOLS = [
    Tool(
        name="get_services",
        description="Get services in a namespace or all namespaces",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace to query (omit for all namespaces)"}
            }
        }
    ),
]


async def _get_services(arguments: dict) -> list[TextContent]:
    namespace = arguments.get("namespace")
    services = (
        v1.list_namespaced_service(namespace) if namespace
        else v1.list_service_for_all_namespaces()
    )

    result = []
    for svc in services.items:
        result.append({
            "name": svc.metadata.name,
            "namespace": svc.metadata.namespace,
            "type": svc.spec.type,
            "cluster_ip": svc.spec.cluster_ip,
            "external_ip": (
                svc.status.load_balancer.ingress[0].ip
                if svc.status.load_balancer.ingress else None
            ),
            "ports": [
                {"port": p.port, "target_port": str(p.target_port), "protocol": p.protocol}
                for p in svc.spec.ports
            ]
        })
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


HANDLERS = {
    "get_services": _get_services,
}
