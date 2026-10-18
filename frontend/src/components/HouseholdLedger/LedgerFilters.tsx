import {useId, useState} from 'react';
import {createPortal} from 'react-dom';
import {CalendarRange, Tag, X} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import type {LedgerFilter} from '../../services/vyvow';
import {localDate} from './ledgerGroups';

export default function LedgerFilters({filter, firstTag, onChange}: {
    filter: LedgerFilter; firstTag: string; onChange: (filter: LedgerFilter) => void;
}) {
    const {t} = useTranslation('main');
    const titleId = useId();
    const [showRange, setShowRange] = useState(false);
    const [from, setFrom] = useState('');
    const [to, setTo] = useState('');
    const openRange = () => {
        setFrom(filter.kind === 'range' ? filter.from : `${localDate().slice(0, 7)}-01`);
        setTo(filter.kind === 'range' ? filter.to : localDate());
        setShowRange(true);
    };
    const maxDate = from ? new Date(`${from}T12:00:00`) : null;
    maxDate?.setDate(maxDate.getDate() + 365);
    return <>
        <footer className="ledger-filter-bar">
            {filter.kind !== 'default' && <button className="ledger-filter-clear" onClick={() => onChange({kind: 'default'})}><X size={14}/>{t('vyvowLedger.clearFilter')}</button>}
            <button className={`ledger-filter-button${filter.kind === 'range' ? ' is-active' : ''}`} aria-label={t('vyvowLedger.dateRange')} aria-pressed={filter.kind === 'range'} onClick={openRange}><CalendarRange size={18}/></button>
            <button className={`ledger-filter-button${filter.kind === 'tag' ? ' is-active' : ''}`} aria-label={t('vyvowLedger.tagOnly')} aria-pressed={filter.kind === 'tag'} onClick={() => onChange(filter.kind === 'tag' ? {kind: 'default'} : {kind: 'tag', tag: firstTag})}><Tag size={18}/></button>
        </footer>
        {showRange && createPortal(<ModalOverlay aria-labelledby={titleId} onClose={() => setShowRange(false)} closeOnBackdrop captureEscape>
            <div className="ledger-entry-modal">
                <header className="ledger-entry-modal-header"><h2 id={titleId}>{t('vyvowLedger.dateRange')}</h2><button className="titlebar-btn" aria-label={t('windowControls.close')} onClick={() => setShowRange(false)}><X size={18}/></button></header>
                <form className="ledger-entry-form" onSubmit={event => {event.preventDefault(); onChange({kind: 'range', from, to}); setShowRange(false);}}>
                    <fieldset>
                        <div className="ledger-form-grid">
                            <label>{t('vyvowLedger.fromDate')}<input autoFocus type="date" required value={from} onChange={event => {setFrom(event.target.value); if (to < event.target.value) setTo('');}}/></label>
                            <label>{t('vyvowLedger.toDate')}<input type="date" required min={from} max={maxDate ? localDate(maxDate) : undefined} value={to} onChange={event => setTo(event.target.value)}/></label>
                        </div>
                        <p className="ledger-status">{t('vyvowLedger.rangeLimit')}</p>
                        <div className="ledger-form-actions"><button type="button" className="modal-action-cancel" onClick={() => setShowRange(false)}>{t('vyvowLedger.cancel')}</button><button className="modal-action-submit" type="submit">{t('vyvowLedger.applyFilter')}</button></div>
                    </fieldset>
                </form>
            </div>
        </ModalOverlay>, document.body)}
    </>;
}
