import {useTranslation} from 'react-i18next';
import type {InputHTMLAttributes} from 'react';
import {formatAmountInput, parseAmountInput} from './amountFormat';

type AmountInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> & {
    value: string;
    onChange: (value: string) => void;
};

export default function AmountInput({value, onChange, ...props}: AmountInputProps) {
    const {i18n} = useTranslation('main');
    const language = i18n.resolvedLanguage || i18n.language;
    return <input {...props} type="text" inputMode="decimal" value={formatAmountInput(value, language)} onChange={event => {
        const input = event.currentTarget;
        const normalized = parseAmountInput(input.value, language);
        if (normalized === null) return;
        const prefixLength = parseAmountInput(input.value.slice(0, input.selectionStart ?? input.value.length), language)?.length ?? normalized.length;
        onChange(normalized);
        requestAnimationFrame(() => {
            if (document.activeElement !== input) return;
            let position = 0;
            while (position < input.value.length && (parseAmountInput(input.value.slice(0, position), language)?.length ?? 0) < prefixLength) position++;
            input.setSelectionRange(position, position);
        });
    }}/>;
}
