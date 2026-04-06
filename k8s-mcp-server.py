#!/usr/bin/env python3
"""
Kubernetes MCP Server - Comprehensive cluster debugging and management
"""
import asyncio
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("k8s-mcp-server")

# Initialize Kubernetes client
try:
    # Try in-cluster config first (for running inside k8s)
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except:
    # Fall back to kubeconfig (for local development)
    config.load_kube_config()
    logger.info("Loaded kubeconfig")

# Initialize API clients
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# Create MCP server
app = Server("k8s-debug-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Kubernetes debugging tools"""
    return [
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
                    "pod_name": {
                        "type": "string",
                        "description": "Name of the pod"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace of the pod",
                        "default": "default"
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name (optional for single-container pods)"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines from the end of logs (default: 100)",
                        "default": 100
                    },
                    "previous": {
                        "type": "boolean",
                        "description": "Get logs from previous container instance (for crashed pods)",
                        "default": False
                    }
                },
                "required": ["pod_name", "namespace"]
            }
        ),
        Tool(
            name="get_nodes",
            description="Get all nodes in the cluster with their status, version, and resources",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_node_logs",
            description="Get events and conditions for a specific node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the node"
                    }
                },
                "required": ["node_name"]
            }
        ),
        Tool(
            name="get_deployments",
            description="Get deployments in a namespace or all namespaces",
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
            name="get_services",
            description="Get services in a namespace or all namespaces",
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
            name="get_events",
            description="Get recent events in a namespace or all namespaces (useful for debugging)",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query (omit for all namespaces)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of events to return (default: 50)",
                        "default": 50
                    }
                }
            }
        ),
        Tool(
            name="describe_pod",
            description="Get detailed information about a specific pod including status, conditions, and events",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod_name": {
                        "type": "string",
                        "description": "Name of the pod"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace of the pod",
                        "default": "default"
                    }
                },
                "required": ["pod_name", "namespace"]
            }
        ),
        Tool(
            name="get_namespaces",
            description="List all namespaces in the cluster",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_resource_usage",
            description="Get resource usage (CPU/Memory) for pods in a namespace (requires metrics-server)",
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
            name="get_persistent_volumes",
            description="Get all persistent volumes and their status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_config_maps",
            description="Get ConfigMaps in a namespace",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query",
                        "default": "default"
                    }
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
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query",
                        "default": "default"
                    }
                },
                "required": ["namespace"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "get_pods":
            namespace = arguments.get("namespace")
            if namespace:
                pods = v1.list_namespaced_pod(namespace)
            else:
                pods = v1.list_pod_for_all_namespaces()

            result = []
            for pod in pods.items:
                container_statuses = pod.status.container_statuses or []
                restarts = sum(cs.restart_count for cs in container_statuses)
                status = pod.status.phase

                # Check for more specific status
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

        elif name == "get_pod_logs":
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

        elif name == "get_nodes":
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

        elif name == "get_node_logs":
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

            # Get events for this node
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

        elif name == "get_deployments":
            namespace = arguments.get("namespace")
            if namespace:
                deployments = apps_v1.list_namespaced_deployment(namespace)
            else:
                deployments = apps_v1.list_deployment_for_all_namespaces()

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

        elif name == "get_services":
            namespace = arguments.get("namespace")
            if namespace:
                services = v1.list_namespaced_service(namespace)
            else:
                services = v1.list_service_for_all_namespaces()

            result = []
            for svc in services.items:
                result.append({
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "external_ip": svc.status.load_balancer.ingress[0].ip if svc.status.load_balancer.ingress else None,
                    "ports": [{"port": p.port, "target_port": str(p.target_port), "protocol": p.protocol} for p in svc.spec.ports]
                })
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_events":
            namespace = arguments.get("namespace")
            limit = arguments.get("limit", 50)

            if namespace:
                events = v1.list_namespaced_event(namespace)
            else:
                events = v1.list_event_for_all_namespaces()

            # Sort by timestamp
            sorted_events = sorted(events.items, key=lambda x: x.last_timestamp or x.event_time, reverse=True)[:limit]

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

        elif name == "describe_pod":
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
                    "conditions": [{"type": c.type, "status": c.status, "reason": c.reason, "message": c.message} for c in (pod.status.conditions or [])],
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

            # Get events for this pod
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

        elif name == "get_namespaces":
            namespaces = v1.list_namespace()
            result = [{"name": ns.metadata.name, "status": ns.status.phase, "age": str(ns.metadata.creation_timestamp)} for ns in namespaces.items]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_resource_usage":
            # This requires metrics-server to be installed
            try:
                from kubernetes import custom_objects_api
                custom_api = client.CustomObjectsApi()
                namespace = arguments.get("namespace")

                if namespace:
                    metrics = custom_api.list_namespaced_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        namespace=namespace,
                        plural="pods"
                    )
                else:
                    metrics = custom_api.list_cluster_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        plural="pods"
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

        elif name == "get_persistent_volumes":
            pvs = v1.list_persistent_volume()
            result = []
            for pv in pvs.items:
                result.append({
                    "name": pv.metadata.name,
                    "capacity": pv.spec.capacity.get("storage"),
                    "access_modes": pv.spec.access_modes,
                    "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
                    "status": pv.status.phase,
                    "claim": f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}" if pv.spec.claim_ref else None,
                    "storage_class": pv.spec.storage_class_name
                })
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_config_maps":
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

        elif name == "get_secrets":
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

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ApiException as e:
        return [TextContent(type="text", text=f"Kubernetes API error: {e.status} - {e.reason}\n{e.body}")]
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the MCP server using SSE transport"""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import Response
    import uvicorn

    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options(),
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ]
    )

    logger.info("K8s MCP Server starting on http://0.0.0.0:8080...")
    config = uvicorn.Config(starlette_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
