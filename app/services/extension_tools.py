"""Credential-free catalog for independently selected extension tools."""
from services.mcp_config import MCP_CATALOG, list_servers


async def extension_tool_catalog() -> list[dict]:
    result = []
    for server in await list_servers():
        entry = MCP_CATALOG.get(server.get('type'))
        if entry is None:  # Uninstalled plugins must disappear even if config remains.
            continue
        config = server.get('config') or {}
        requires_key = server['type'] == 'web_search' and not str(config.get('api_key') or '').strip()
        result.append({
            'id': server['id'], 'type': server['type'],
            'name': config.get('name') or entry.get('label') or server['type'],
            'can_enable': not requires_key,
        })
    return result
