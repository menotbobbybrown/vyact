import {useTranslation} from 'react-i18next';
import CustomSelect from '../CustomSelect/CustomSelect';
import type {LedgerCurrency} from '../../services/vyvow';
import {countryFlag, currencyCountry} from './ledgerCurrency';

export default function LedgerCurrencySelect({value, currencies, onChange}: {
    value: string; currencies: LedgerCurrency[]; onChange: (value: string) => void;
}) {
    const {t, i18n} = useTranslation('main');
    const regionNames = new Intl.DisplayNames([i18n.language], {type: 'region'});
    const options = [...new Set([value, ...currencies.map(item => item.currencyCode)])].map(code => {
        const country = currencyCountry(code, currencies);
        return {value: code, label: [countryFlag(country), code].filter(Boolean).join(' '),
            description: country ? regionNames.of(country) : undefined};
    });
    return <CustomSelect ariaLabel={t('vyvowLedger.currency')} searchable value={value} options={options} onChange={onChange}/>;
}
