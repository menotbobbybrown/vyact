import {useTranslation} from 'react-i18next';
import {countryFlag, currencyCountry} from './ledgerCurrency';
import type {LedgerCurrency} from '../../services/vyvow';

export default function LedgerMoney({amount, currency, currencies}: {
    amount: number; currency: string; currencies: LedgerCurrency[];
}) {
    const {i18n} = useTranslation('main');
    const flag = countryFlag(currencyCountry(currency, currencies));
    return <span className="ledger-money">
        {flag && <span className="ledger-currency-flag" aria-hidden="true">{flag}</span>}
        <span>{new Intl.NumberFormat(i18n.language, {style: 'currency', currency, currencyDisplay: flag ? 'narrowSymbol' : 'code'}).format(amount)}</span>
    </span>;
}
