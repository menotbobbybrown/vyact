import {PROJECTION_STORAGE_KEY, type ProjectionInputs} from './projection';

type ProjectionSnapshot = {inputs: ProjectionInputs; profileNameOverridden: boolean};
let pendingWrite: Promise<unknown> = Promise.resolve();

/** Serialize updates so a slow save cannot overwrite a later reset. */
export function persistProjection(snapshot: ProjectionSnapshot | null): Promise<void> {
    const operation = pendingWrite.catch(() => {}).then(async () => {
        const response = await fetch('/api/wealth-lab', snapshot ? {
            method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(snapshot),
        } : {method: 'DELETE'});
        if (!response.ok) throw new Error('Wealth Lab persistence failed');
    });
    pendingWrite = operation;
    return operation;
}

/** Called only after restoring settings, never when opening Wealth Lab. */
export async function restoreProjectionCache(): Promise<void> {
    await pendingWrite.catch(() => {});
    const response = await fetch('/api/wealth-lab');
    if (!response.ok) throw new Error('Wealth Lab restore failed');
    const {snapshot} = await response.json();
    if (snapshot) {
        localStorage.setItem(PROJECTION_STORAGE_KEY, JSON.stringify({...snapshot.inputs, profileNameOverridden: snapshot.profileNameOverridden}));
    }
}
