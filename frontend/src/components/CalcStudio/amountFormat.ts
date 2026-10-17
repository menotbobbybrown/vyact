function numberSeparators(language: string) {
    const parts = new Intl.NumberFormat(language).formatToParts(12345.6);
    return {
        group: parts.find(part => part.type === 'group')?.value || ',',
        decimal: parts.find(part => part.type === 'decimal')?.value || '.',
    };
}

export function parseAmountInput(value: string, language: string): string | null {
    const {group, decimal} = numberSeparators(language);
    const normalized = value.split(group).join('').replace(/[\s\u00a0\u202f]/g, '').split(decimal).join('.');
    return /^\d*(\.\d*)?$/.test(normalized) ? normalized : null;
}

export function formatAmountInput(value: string, language: string): string {
    if (!value) return '';
    const {decimal} = numberSeparators(language);
    const [integer, fraction] = value.split('.');
    if (!/^\d*$/.test(integer) || (fraction !== undefined && !/^\d*$/.test(fraction))) return value;
    const grouped = integer ? new Intl.NumberFormat(language, {maximumFractionDigits: 0}).format(BigInt(integer)) : '';
    return grouped + (fraction !== undefined ? decimal + fraction : '');
}
