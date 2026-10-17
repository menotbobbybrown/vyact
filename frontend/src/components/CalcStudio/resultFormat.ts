const COMPACT_THRESHOLDS: Record<string, number> = {
    ko: 100_000_000,
    ja: 10_000,
    zh: 10_000,
};

export function formatProjectionAmount(value: number, language: string): string {
    const baseLanguage = language.toLowerCase().split(/[-_]/)[0];
    const threshold = COMPACT_THRESHOLDS[baseLanguage] ?? 1_000_000;
    if (Math.abs(value) < threshold) {
        return new Intl.NumberFormat(language, {maximumFractionDigits: 0}).format(Math.trunc(value) || 0);
    }
    if (baseLanguage === 'ko') {
        return `${new Intl.NumberFormat(language, {maximumFractionDigits: 2}).format(value / 100_000_000)}억`;
    }
    return new Intl.NumberFormat(language, {notation: 'compact', compactDisplay: 'short', maximumFractionDigits: 2}).format(value);
}
