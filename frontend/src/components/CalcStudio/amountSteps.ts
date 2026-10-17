const DEFAULT_AMOUNT_STEPS = [1_000_000_000, 1_000_000, 1_000] as const;
const LOCAL_AMOUNT_STEPS: Record<string, readonly number[]> = {
    ko: [100_000_000, 10_000_000, 1_000_000],
    ja: [100_000_000, 10_000, 1_000],
    zh: [100_000_000, 10_000, 1_000],
};

export function getAmountSteps(language: string) {
    const baseLanguage = language.toLowerCase().split(/[-_]/)[0];
    const formatter = new Intl.NumberFormat(language, {notation: 'compact', compactDisplay: 'short', maximumFractionDigits: 0});
    return (LOCAL_AMOUNT_STEPS[baseLanguage] || DEFAULT_AMOUNT_STEPS).map(value => ({
        value,
        label: `+${formatter.format(value)}`,
    }));
}
