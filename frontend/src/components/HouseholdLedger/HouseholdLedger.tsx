import {useEffect, useMemo, useState, type CSSProperties} from 'react';
import {useTranslation} from 'react-i18next';
import {ChevronLeft, ChevronRight, Plus, RefreshCw, Wallet, X} from 'lucide-react';
import CustomSelect from '../CustomSelect/CustomSelect';
import {searchLedger, VYVOW_TOKEN_CHANGED, type LedgerData, type LedgerEntry, type LedgerPeriod} from '../../services/vyvow';
import {convertedAmount, groupEntries, localDate} from './ledgerGroups';
import LedgerEntryForm, {ledgerErrorKey} from './LedgerEntryForm';
import '../common/ModalOverlay/ModalActions.css';
import './HouseholdLedger.css';

export default function HouseholdLedger({onClose, style}: {onClose: () => void; style?: CSSProperties}) {
    const {t, i18n} = useTranslation('main');
    const [month, setMonth] = useState(() => localDate().slice(0, 7));
    const [period, setPeriod] = useState<LedgerPeriod>('daily');
    const [currency, setCurrency] = useState('KRW');
    const [data, setData] = useState<LedgerData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [revision, setRevision] = useState(0);
    const [editing, setEditing] = useState<LedgerEntry | null | undefined>(undefined);
    useEffect(() => {
        const controller = new AbortController();
        setLoading(true); setError(''); setData(null); setEditing(undefined);
        searchLedger(`${month}-01`, period, currency, controller.signal).then(result => {
            if (!controller.signal.aborted) setData(result);
        }).catch(cause => { if (!controller.signal.aborted) setError(ledgerErrorKey(cause)); })
            .finally(() => { if (!controller.signal.aborted) setLoading(false); });
        return () => controller.abort();
    }, [month, period, currency, revision]);
    useEffect(() => {
        const handleChange = () => {setEditing(undefined); setData(null); setRevision(value => value + 1);};
        window.addEventListener(VYVOW_TOKEN_CHANGED, handleChange);
        return () => window.removeEventListener(VYVOW_TOKEN_CHANGED, handleChange);
    }, []);
    const groups = useMemo(() => groupEntries(data?.entries || [], period), [data, period]);
    const totals = useMemo(() => {
        let income = 0, expense = 0, missing = false;
        for (const entry of data?.entries || []) {
            const value = convertedAmount(entry, currency);
            if (value === null) {missing = true; continue;}
            if (entry.txType === 'INCOME') income += value;
            else expense += value;
        }
        return {income, expense, missing};
    }, [data, currency]);
    const formatMoney = (value: number, unit = currency) => new Intl.NumberFormat(i18n.language, {style: 'currency', currency: unit}).format(value);
    const movePeriod = (direction: number) => {
        const date = new Date(`${month}-01T12:00:00`);
        if (period === 'monthly') date.setFullYear(date.getFullYear() + direction);
        else date.setMonth(date.getMonth() + direction);
        setMonth(localDate(date).slice(0, 7));
    };
    const groupLabel = (key: string) => {
        const date = new Date(`${key.length === 7 ? `${key}-01` : key}T12:00:00`);
        return new Intl.DateTimeFormat(i18n.language, period === 'monthly' ? {year: 'numeric', month: 'long'} : {month: 'short', day: 'numeric', weekday: 'short'}).format(date)
            + (period === 'weekly' ? ` · ${t('vyvowLedger.week')}` : '');
    };
    const currencies = [...new Set([currency, ...(data?.currencies.map(item => item.currencyCode) || [])])];
    return <aside className="household-ledger" style={style} aria-labelledby="household-ledger-title">
        <header className="ledger-header"><Wallet size={20} aria-hidden="true"/><h2 id="household-ledger-title">{t('vyvowLedger.title')}</h2>
            <button className="titlebar-btn" onClick={onClose} aria-label={t('windowControls.close')}><X size={18}/></button></header>
        <div className="ledger-body">
            <div className="ledger-toolbar">
                <CustomSelect ariaLabel={t('vyvowLedger.currency')} searchable value={currency} options={currencies.map(value => ({value, label: value}))} onChange={setCurrency}/>
                <div className="ledger-period-nav">
                    <button className="titlebar-btn" onClick={() => movePeriod(-1)} aria-label={t('vyvowLedger.previous')}><ChevronLeft size={18}/></button>
                    <strong>{new Intl.DateTimeFormat(i18n.language, period === 'monthly' ? {year: 'numeric'} : {year: 'numeric', month: 'long'}).format(new Date(`${month}-01T12:00:00`))}</strong>
                    <button className="titlebar-btn" onClick={() => movePeriod(1)} aria-label={t('vyvowLedger.next')}><ChevronRight size={18}/></button>
                </div>
                <button className="titlebar-btn" disabled={loading} onClick={() => setRevision(value => value + 1)} aria-label={t('vyvowLedger.refresh')}><RefreshCw size={16}/></button>
            </div>
            <div className="ledger-tabs" role="group" aria-label={t('vyvowLedger.period')}>
                {(['daily', 'weekly', 'monthly'] as const).map(value => <button key={value} aria-pressed={period === value} onClick={() => setPeriod(value)}>{t(`vyvowLedger.${value}`)}</button>)}
            </div>
            {loading && <p role="status" className="ledger-status">{t('vyvowLedger.loading')}</p>}
            {error && <p role="alert" className="ledger-error">{t(error)}</p>}
            {!loading && !error && data && <>
                <div className="ledger-summary">{(['income', 'expense'] as const).map(key => <div key={key}><span>{t(`vyvowLedger.${key === 'income' ? 'INCOME' : 'EXPENSE'}`)}</span><strong className={`ledger-${key}`}>{formatMoney(totals[key])}</strong></div>)}</div>
                {totals.missing && <p className="ledger-status">{t('vyvowLedger.missingRate')}</p>}
                {editing !== undefined ? <LedgerEntryForm key={editing?.id || 'new'} entry={editing} currency={currency} currencies={currencies} tags={data.tags}
                    onCancel={() => setEditing(undefined)} onSaved={() => {setEditing(undefined); setRevision(value => value + 1);}}/>
                    : <>
                        <button className="ledger-add modal-action-submit" onClick={() => setEditing(null)}><Plus size={16}/>{t('vyvowLedger.add')}</button>
                        {!groups.length && <p className="ledger-status">{t('vyvowLedger.empty')}</p>}
                        {groups.map(([key, entries]) => <section className="ledger-group" key={key}>
                            <h3>{groupLabel(key)}</h3>
                            {entries.map(entry => <button className="ledger-entry" key={entry.id} onClick={() => setEditing(entry)}>
                                <span className="ledger-entry-description"><strong>{t(`vyvowLedger.categories.op${entry.houseLedgerOptionId}`)}</strong>{entry.memo && <span>{entry.memo}</span>}{entry.tag && <small>#{entry.tag}</small>}</span>
                                <span className={entry.txType === 'INCOME' ? 'ledger-income' : 'ledger-expense'}>{entry.txType === 'INCOME' ? '+' : '−'}{formatMoney(entry.amount, entry.currency)}</span>
                            </button>)}
                        </section>)}
                    </>}
            </>}
        </div>
    </aside>;
}
