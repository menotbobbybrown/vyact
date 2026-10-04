import {toast} from '../components/common/ToastNotifications/ToastNotifications';

const DECISION_WARNING_DURATION_MS = 12_000;
let lastWarningMessage: string | undefined;
let lastWarningAt = 0;

export function showDecisionWarning(title: string, message?: string): void {
    const now = Date.now();
    if (message === lastWarningMessage && now - lastWarningAt < DECISION_WARNING_DURATION_MS) return;
    lastWarningMessage = message;
    lastWarningAt = now;
    toast.warning(title, message, DECISION_WARNING_DURATION_MS);
}
