import ModalTabs from '../common/ModalTabs/ModalTabs';
import DateInput from '../common/DateInput/DateInput';
import {createPortal} from 'react-dom';
import {X} from 'lucide-react';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import {useEffect, useId, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import LedgerCurrencySelect from './LedgerCurrencySelect';
import CustomSelect from '../CustomSelect/CustomSelect';
import ConfirmModal from '../common/ConfirmModal/ConfirmModal';
import {deleteLedgerEntry, EXPENSE_CATEGORIES, INCOME_CATEGORIES, saveLedgerEntry, type LedgerCurrency, type LedgerEntry} from '../../services/vyvow';
import {localDate} from './ledgerGroups';
import {ApiError} from '../../utils/apiError';

export function ledgerErrorKey(error: unknown) {
    return error instanceof ApiError && error.detail?.startsWith('vyvowLedger.') ? error.detail : 'vyvowLedger.requestFailed';
}

export default function LedgerEntryForm({entry, currency, currencies, tags, onSaved, onCancel}: {
    entry: LedgerEntry | null; currency: string; currencies: LedgerCurrency[]; tags: string[];
    onSaved: () => void; onCancel: () => void;
}) {
    const {t} = useTranslation('main');
    const titleId = useId();
    const modalRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        const previous = document.activeElement as HTMLElement | null;
        modalRef.current?.focus();
        return () => previous?.focus();
    }, []);
    const [draft, setDraft] = useState<LedgerEntry>(() => entry || {
        id: 0, txType: 'EXPENSE', houseLedgerOptionId: EXPENSE_CATEGORIES[0], memberBoardFileId: 0,
        currency, amount: 0, memo: '', tag: '', createdAt: localDate(),
    });
    const [amount, setAmount] = useState(entry ? String(entry.amount) : '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [confirmDelete, setConfirmDelete] = useState(false);
    const categories = draft.txType === 'EXPENSE' ? EXPENSE_CATEGORIES : INCOME_CATEGORIES;
    const update = <K extends keyof LedgerEntry>(key: K, value: LedgerEntry[K]) => setDraft(previous => ({...previous, [key]: value}));
    const submit = async (remove = false) => {
        if (busy) return;
        setBusy(true); setError('');
        try {
            if (remove) await deleteLedgerEntry(draft.id);
            else await saveLedgerEntry({...draft, amount: Number(amount)});
            onSaved();
        } catch (cause) { setError(ledgerErrorKey(cause)); }
        finally { setBusy(false); setConfirmDelete(false); }
    };
    return createPortal(<ModalOverlay className="ledger-entry-overlay" aria-labelledby={titleId}
        onClose={busy ? undefined : onCancel} closeOnBackdrop={!busy} captureEscape>
        <div className="ledger-entry-modal" ref={modalRef} tabIndex={-1} onKeyDown={event => {
            if (event.key !== 'Tab') return;
            const elements = modalRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), [tabindex="0"]');
            if (!elements?.length) return;
            const first = elements[0], last = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
            else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
        }}>
        <header className="ledger-entry-modal-header"><h2 id={titleId}>{t(entry ? 'vyvowLedger.edit' : 'vyvowLedger.add')}</h2>
            <button className="titlebar-btn" type="button" onClick={onCancel} disabled={busy} aria-label={t('windowControls.close')}><X size={18}/></button></header>
        <form className="ledger-entry-form" onSubmit={event => {event.preventDefault(); void submit();}}>
        <fieldset disabled={busy}>
            <div className="ledger-type-tabs" role="group" aria-label={t('vyvowLedger.type')}>
                <ModalTabs tabs={(['EXPENSE', 'INCOME'] as const).map(key => ({key, label: <span className={key === 'EXPENSE' ? 'ledger-expense' : 'ledger-income'}>{t(`vyvowLedger.${key}`)}</span>}))}
                    activeKey={draft.txType} disabled={busy} onChange={txType => {
                        if (txType === draft.txType) return;
                        setDraft(previous => ({...previous, txType, houseLedgerOptionId: txType === 'EXPENSE' ? EXPENSE_CATEGORIES[0] : INCOME_CATEGORIES[0]}));
                    }}/>
            </div>
            <div className="ledger-form-grid">
                <div className="ledger-form-field"><span>{t('vyvowLedger.date')}</span><DateInput label={t('vyvowLedger.date')} required value={draft.createdAt.slice(0, 10)} onChange={value => update('createdAt', value)}/></div>
                <div className="ledger-form-field"><span>{t('vyvowLedger.category')}</span><CustomSelect portal ariaLabel={t('vyvowLedger.category')} value={String(draft.houseLedgerOptionId)} options={categories.map(id => ({value: String(id), label: t(`vyvowLedger.categories.op${id}`)}))} onChange={value => update('houseLedgerOptionId', Number(value))}/></div>
                <div className="ledger-form-field"><span>{t('vyvowLedger.amount')}</span><input aria-label={t('vyvowLedger.amount')} type="number" min="0" max="100000000000000" step="any" required value={amount} onChange={event => setAmount(event.target.value)}/></div>
                <div className="ledger-form-field"><span>{t('vyvowLedger.currency')}</span><LedgerCurrencySelect value={draft.currency} currencies={currencies} onChange={value => update('currency', value)}/></div>
            </div>
            <div className="ledger-form-field"><span>{t('vyvowLedger.memo')}</span><input aria-label={t('vyvowLedger.memo')} maxLength={120} value={draft.memo || ''} onChange={event => update('memo', event.target.value)}/></div>
            <div className="ledger-form-field"><span>{t('vyvowLedger.tag')}</span>
                <CustomSelect portal searchable allowCustomValue searchMaxLength={25} clearable
                    ariaLabel={t('vyvowLedger.tag')} placeholder={t('vyvowLedger.tag')}
                    value={draft.tag || ''} options={tags.map(tag => ({value: tag, label: tag}))}
                    onChange={value => update('tag', value)} onClear={() => update('tag', '')}/>
            </div>
            {error && <p role="alert" className="ledger-error">{t(error)}</p>}
            <div className="ledger-form-actions">
                {draft.id > 0 && <button type="button" className="modal-action-danger" onClick={() => setConfirmDelete(true)}>{t('vyvowLedger.delete')}</button>}
                <button type="button" className="modal-action-cancel" onClick={onCancel}>{t('vyvowLedger.cancel')}</button>
                <button type="submit" className="modal-action-submit">{t(busy ? 'vyvowLedger.saving' : 'vyvowLedger.save')}</button>
            </div>
        </fieldset>
        {confirmDelete && <ConfirmModal title={t('vyvowLedger.deleteConfirm')} loading={busy} loadingValue="delete" actionLayout="horizontal"
            options={[{value: 'cancel', label: t('vyvowLedger.cancel')}, {value: 'delete', label: t('vyvowLedger.delete'), variant: 'danger'}]}
            onClose={() => setConfirmDelete(false)} onSelect={value => value === 'delete' ? void submit(true) : setConfirmDelete(false)}/>}
    </form>
    </div></ModalOverlay>, document.body);
}
