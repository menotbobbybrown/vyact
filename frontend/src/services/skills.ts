import i18n from '../i18n';

export interface Skill {
    id: string;
    name: string;
    description: string;
    instructions: string;
    enabled: boolean;
    origin?: 'builtin' | 'user';
    version?: number;
    created_at: string;
    updated_at: string;
}

let cachedSkills: Skill[] | null = null;
let pendingSkillsRequest: Promise<Skill[]> | null = null;

async function requestSkills(): Promise<Skill[]> {
    const response = await fetch('/api/skills');
    if (!response.ok) throw new Error(i18n.t('main:networkError.requestFailed'));
    const skills = await response.json();
    return updateSkillsCache(skills);
}

export function getSkills(): Promise<Skill[]> {
    if (cachedSkills) return Promise.resolve(cachedSkills);
    if (!pendingSkillsRequest) {
        pendingSkillsRequest = requestSkills().finally(() => {
            pendingSkillsRequest = null;
        });
    }
    return pendingSkillsRequest;
}

export function refreshSkills(): Promise<Skill[]> {
    if (pendingSkillsRequest) return pendingSkillsRequest;
    pendingSkillsRequest = requestSkills().finally(() => {
        pendingSkillsRequest = null;
    });
    return pendingSkillsRequest;
}

export function updateSkillsCache(skills: Skill[]): Skill[] {
    cachedSkills = [...skills].sort((left, right) => {
        const originOrder = Number(left.origin === 'builtin') - Number(right.origin === 'builtin');
        const createdAt = (skill: Skill) => Date.parse(skill.created_at) || 0;
        return originOrder || createdAt(right) - createdAt(left) || left.id.localeCompare(right.id);
    });
    return cachedSkills;
}
