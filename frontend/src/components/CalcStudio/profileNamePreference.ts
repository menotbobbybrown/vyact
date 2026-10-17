import {PROJECTION_STORAGE_KEY} from './projection';

export function loadProfileNameOverride(): boolean {
    try {
        const saved = JSON.parse(localStorage.getItem(PROJECTION_STORAGE_KEY) || '{}');
        return typeof saved?.profileNameOverridden === 'boolean'
            ? saved.profileNameOverridden
            : typeof saved?.profileName === 'string' && saved.profileName.trim() !== '';
    } catch { return false; }
}
