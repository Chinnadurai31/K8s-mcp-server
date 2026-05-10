#!/usr/bin/env python3
import asyncio
import logging
from server import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("k8s-mcp-server")


async def main():
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
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
    uvicorn_config = uvicorn.Config(starlette_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
