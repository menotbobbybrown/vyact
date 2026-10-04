import type {DecisionConnectionProtocol} from '../services/api';

export const DECISION_CONNECTION_FORMATS: Record<DecisionConnectionProtocol, {label: string; baseUrl: string; model: string; docsUrl: string}> = {
    typesafe: {label: 'TypeSafe', baseUrl: 'https://api.typesafe.ai/v1', model: 'jev-latest', docsUrl: 'https://api.typesafe.ai/docs'},
    vercel: {label: 'Vercel AI Gateway', baseUrl: 'https://ai-gateway.vercel.sh/v4/ai', model: 'typesafe-ai/jev', docsUrl: 'https://vercel.com/ai-gateway/models/jev'},
};

export const DECISION_CONNECTION_OPTIONS = Object.entries(DECISION_CONNECTION_FORMATS).map(([value, format]) => ({value, label: format.label}));
