import type {LedgerCurrency} from '../../services/vyvow';

export function currencyCountry(currency: string, currencies: LedgerCurrency[]): string {
    const country = currencies.find(item => item.currencyCode === currency)?.isoAlpha2?.toUpperCase() || '';
    return /^[A-Z]{2}$/.test(country) ? country : '';
}

export function countryFlag(country: string): string {
    return country ? String.fromCodePoint(...[...country].map(letter => 127397 + letter.charCodeAt(0))) : '';
}
