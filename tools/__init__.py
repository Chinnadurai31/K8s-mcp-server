from . import pods, nodes, workloads, networking, events, cluster, configs

_MODULES = [pods, nodes, workloads, networking, events, cluster, configs]

TOOLS = [tool for module in _MODULES for tool in module.TOOLS]

_HANDLERS = {name: fn for module in _MODULES for name, fn in module.HANDLERS.items()}


async def dispatch(name: str, arguments: dict):
    handler = _HANDLERS.get(name)
    if handler is None:
        return None
    return await handler(arguments)
