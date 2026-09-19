const SEPARATE_SETTINGS_TYPES = new Set(['google_workspace', 'microsoft_workspace']);

export function hasSeparateMcpSettings(type: string): boolean {
    return SEPARATE_SETTINGS_TYPES.has(type);
}

/** Preserve saved order within each group; separately managed integrations come last. */
export function orderMcpServersForDisplay<T extends {type: string}>(servers: readonly T[]): T[] {
    return [
        ...servers.filter(server => !hasSeparateMcpSettings(server.type)),
        ...servers.filter(server => hasSeparateMcpSettings(server.type)),
    ];
}
