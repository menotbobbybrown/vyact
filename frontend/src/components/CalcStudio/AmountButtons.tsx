import {useTranslation} from 'react-i18next';
import {RotateCcw} from 'lucide-react';
import {getAmountSteps} from './amountSteps';

interface AmountButtonsProps {
    fieldLabel: string;
    onAdjust: (amount: number | null) => void;
}

export default function AmountButtons({fieldLabel, onAdjust}: AmountButtonsProps) {
    const {t, i18n} = useTranslation('main');
    return <div className="calc-studio-amount-buttons" role="group" aria-label={fieldLabel}>
        {getAmountSteps(i18n.resolvedLanguage || i18n.language).map(({value, label}) =>
            <button key={value} type="button" className="modal-action-cancel" onClick={() => onAdjust(value)}>{label}</button>)}
        <button type="button" className="modal-action-cancel" title={t('calcStudio.reset')} aria-label={`${fieldLabel}: ${t('calcStudio.reset')}`} onClick={() => onAdjust(null)}>
            <RotateCcw size={13} aria-hidden="true"/>
        </button>
    </div>;
}
