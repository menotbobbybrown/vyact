import {api} from './api';
import {assertOk} from '../utils/apiError';

export const VYVOW_TOKEN_CHANGED = 'vyact:vyvow-token-changed';
export const HOUSEHOLD_LEDGER_PANEL_ID = 'vyvow-household-ledger';
export const EXPENSE_CATEGORIES = [1, 2, 3, 12, 4, 5, 13, 6];
export const INCOME_CATEGORIES = [7, 8, 9, 10, 11];
export type LedgerPeriod = 'daily' | 'weekly' | 'monthly';
export interface LedgerEntry {
    id: number;
    txType: 'INCOME' | 'EXPENSE';
    houseLedgerOptionId: number;
    memberBoardFileId: number;
    currency: string;
    amount: number;
    memo: string;
    tag: string;
    createdAt: string;
    targetCurrency?: string;
    rate?: number;
    targetRate?: number;
}
export interface LedgerData {
    entries: LedgerEntry[];
    currencies: {currencyCode: string}[];
    tags: string[];
}

async function request<T>(path: string, method: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    const response = await fetch(`/api/vyvow/ledger${path}`, {
        method, headers: {'Content-Type': 'application/json'},
        body: body === undefined ? undefined : JSON.stringify(body), signal,
    });
    await assertOk(response);
    return response.json();
}

export const searchLedger = (fromDate: string, period: LedgerPeriod, currency: string, signal?: AbortSignal) =>
    request<LedgerData>('/search', 'POST', {fromDate, period, tempTargetCurrency: currency}, signal);
export const saveLedgerEntry = (entry: LedgerEntry) => request('', 'PUT', entry);
export const deleteLedgerEntry = (id: number) => request(`/${id}`, 'DELETE');

export async function saveVyvowToken(token: string) {
    const status = await api.saveVyvowToken(token);
    window.dispatchEvent(new CustomEvent(VYVOW_TOKEN_CHANGED, {detail: status.has_token}));
    return status;
}
