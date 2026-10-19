import {Plus, Trash2} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import CustomSelect from '../CustomSelect/CustomSelect';
import AmountInput from './AmountInput';
import {incomeSourceError, MAX_INCOME_SOURCES, type IncomeSource} from './projection';

export default function IncomeSources({sources, onChange, currentAge, endAge, birthYear, validAgeRange, showErrors}: {
    sources: IncomeSource[]; onChange: (sources: IncomeSource[]) => void; currentAge: number;
    endAge: number; birthYear: number; validAgeRange: boolean; showErrors: boolean;
}) {
    const {t} = useTranslation('main');
    const update = (id: string, field: keyof IncomeSource, value: string) => onChange(sources.map(source => source.id === id ? {...source, [field]: value} : source));
    const ageOptions = (minimum: number) => Array.from({length: validAgeRange ? Math.max(0, endAge - minimum + 1) : 0}, (_, index) => {
        const age = minimum + index;
        return {value: String(age), label: t('calcStudio.ageAndYear', {age, year: birthYear + age})};
    });
    return <div className="wealth-income-sources">
        <div className="wealth-income-heading"><strong>{t('calcStudio.regularIncome')}</strong>
            <button type="button" className="modal-action-cancel wealth-income-add" disabled={sources.length >= MAX_INCOME_SOURCES} onClick={() => onChange([...sources, {id: crypto.randomUUID(), name: '', monthlyAmount: '', startAge: '', endAge: ''}])}><Plus size={14}/>{t('calcStudio.addIncome')}</button>
        </div>
        {sources.map((source, index) => {
            const error = showErrors ? incomeSourceError(source, currentAge, endAge) : null;
            const prefix = `wealth-income-${source.id}`;
            return <div className="wealth-income-card" key={source.id}>
                <div className="wealth-income-card-heading"><span>{t('calcStudio.incomeNumber', {number: index + 1})}</span>
                    <button type="button" className="wealth-income-delete" aria-label={t('calcStudio.removeIncome', {number: index + 1})} onClick={() => onChange(sources.filter(item => item.id !== source.id))}><Trash2 size={14}/></button>
                </div>
                <div className="calc-studio-fields">
                    <div className="calc-studio-field"><label htmlFor={`${prefix}-name`}>{t('calcStudio.incomeName')}</label>
                        <input id={`${prefix}-name`} maxLength={80} value={source.name} onChange={event => update(source.id, 'name', event.target.value)}/></div>
                    <div className="calc-studio-field"><label htmlFor={`${prefix}-amount`}>{t('calcStudio.monthlyIncome')}</label>
                        <AmountInput id={`${prefix}-amount`} aria-invalid={error === 'monthlyAmount'} placeholder={error === 'monthlyAmount' ? t('calcStudio.enterMonthlyIncome') : undefined} value={source.monthlyAmount} onChange={value => update(source.id, 'monthlyAmount', value)}/></div>
                    {(['startAge', 'endAge'] as const).map(field => {
                        const invalid = error === field;
                        const label = field === 'startAge' ? 'incomeStartAge' : 'incomeEndAge';
                        const prompt = invalid ? field === 'startAge' ? 'selectIncomeAge' : 'selectIncomeEndAge' : label;
                        return <div className="calc-studio-field" key={field}><label>{t(`calcStudio.${label}`)}</label>
                            <CustomSelect value={source[field]} disabled={!validAgeRange} options={ageOptions(field === 'endAge' ? Math.max(currentAge + 1, Number(source.startAge) || 0) : currentAge + 1)}
                                searchable portal clearable className={invalid ? 'calc-studio-control-error' : ''}
                                ariaLabel={t(`calcStudio.${prompt}`)} placeholder={field === 'endAge' && !invalid ? t('calcStudio.untilPlanEnd', {age: Number.isFinite(endAge) ? endAge : ''}) : t(`calcStudio.${prompt}`)}
                                onClear={() => update(source.id, field, '')} onChange={value => update(source.id, field, value)}/>
                        </div>;
                    })}
                </div>
            </div>;
        })}
    </div>;
}
