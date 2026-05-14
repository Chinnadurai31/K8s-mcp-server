#!/usr/bin/env python3
import asyncio
import logging
from server import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("k8s-mcp-server")


async def main():
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(scope, receive, send):
        async with sse.connect_sse(scope, receive, send) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options(),
            )

    starlette_app = Starlette(
        routes=[
            Mount("/sse", app=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ]
    )

    logger.info("K8s MCP Server starting on http://0.0.0.0:8080...")
    uvicorn_config = uvicorn.Config(starlette_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
