import type {ProjectionInputs} from './projection';
export interface SavedPlan {
    id: string;
    name: string;
    updatedAt: string;
    inputs: ProjectionInputs;
    profileNameOverridden: boolean;
}
async function request(path = '', options?: RequestInit) {
    const response = await fetch(`/api/wealth-lab/plans${path}`, options);
    if (!response.ok) throw new Error('Saved plan request failed');
    return response.json();
}
export async function listSavedPlans(): Promise<SavedPlan[]> {
    return (await request()).plans;
}
export async function savePlan(name: string, inputs: ProjectionInputs, profileNameOverridden: boolean, id?: string): Promise<SavedPlan> {
    return (await request(id ? `/${id}` : '', {
        method: id ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, inputs, profileNameOverridden}),
    })).plan;
}
export async function deletePlan(id: string): Promise<void> {
    await request(`/${id}`, {method: 'DELETE'});
}
