import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from kubernetes.client.rest import ApiException
from tools import TOOLS, dispatch

logger = logging.getLogger("k8s-mcp-server")

app = Server("k8s-debug-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    try:
        result = await dispatch(name, arguments)
        if result is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        return result
    except ApiException as e:
        return [TextContent(type="text", text=f"Kubernetes API error: {e.status} - {e.reason}\n{e.body}")]
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
