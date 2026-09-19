/** User-defined names apply to both local and remote custom MCP servers. */
export function getCustomMcpName(server: {type: string; config?: Record<string, unknown>}): string | undefined {
    if (server.type !== 'custom' && server.type !== 'custom_remote') return undefined;
    const name = server.config?.name;
    return typeof name === 'string' && name.trim() ? name : undefined;
}
