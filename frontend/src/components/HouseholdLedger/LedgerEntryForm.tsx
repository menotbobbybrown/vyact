import {useState} from 'react';
import {useTranslation} from 'react-i18next';
import CustomSelect from '../CustomSelect/CustomSelect';
import ConfirmModal from '../common/ConfirmModal/ConfirmModal';
import {deleteLedgerEntry, EXPENSE_CATEGORIES, INCOME_CATEGORIES, saveLedgerEntry, type LedgerEntry} from '../../services/vyvow';
import {localDate} from './ledgerGroups';
import {ApiError} from '../../utils/apiError';

export function ledgerErrorKey(error: unknown) {
    return error instanceof ApiError && error.detail?.startsWith('vyvowLedger.') ? error.detail : 'vyvowLedger.requestFailed';
}

export default function LedgerEntryForm({entry, currency, currencies, tags, onSaved, onCancel}: {
    entry: LedgerEntry | null; currency: string; currencies: string[]; tags: string[];
    onSaved: () => void; onCancel: () => void;
}) {
    const {t} = useTranslation('main');
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
    return <form className="ledger-entry-form" onSubmit={event => {event.preventDefault(); void submit();}}>
        <fieldset disabled={busy}>
            <CustomSelect ariaLabel={t('vyvowLedger.type')} value={draft.txType} options={['EXPENSE', 'INCOME'].map(value => ({value, label: t(`vyvowLedger.${value}`)}))}
                onChange={value => setDraft(previous => ({...previous, txType: value as LedgerEntry['txType'], houseLedgerOptionId: value === 'EXPENSE' ? EXPENSE_CATEGORIES[0] : INCOME_CATEGORIES[0]}))}/>
            <div className="ledger-form-grid">
                <label>{t('vyvowLedger.date')}<input type="date" required value={draft.createdAt.slice(0, 10)} onChange={event => update('createdAt', event.target.value)}/></label>
                <label>{t('vyvowLedger.category')}<CustomSelect value={String(draft.houseLedgerOptionId)} options={categories.map(id => ({value: String(id), label: t(`vyvowLedger.categories.op${id}`)}))} onChange={value => update('houseLedgerOptionId', Number(value))}/></label>
                <label>{t('vyvowLedger.amount')}<input type="number" min="0" max="100000000000000" step="any" required value={amount} onChange={event => setAmount(event.target.value)}/></label>
                <label>{t('vyvowLedger.currency')}<CustomSelect searchable value={draft.currency} options={[...new Set([...currencies, draft.currency])].map(value => ({value, label: value}))} onChange={value => update('currency', value)}/></label>
            </div>
            <label>{t('vyvowLedger.memo')}<input maxLength={120} value={draft.memo || ''} onChange={event => update('memo', event.target.value)}/></label>
            <label>{t('vyvowLedger.tag')}<input list="ledger-tags" maxLength={25} value={draft.tag || ''} onChange={event => update('tag', event.target.value)}/></label>
            <datalist id="ledger-tags">{tags.map(tag => <option key={tag} value={tag}/>)}</datalist>
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
    </form>;
}
