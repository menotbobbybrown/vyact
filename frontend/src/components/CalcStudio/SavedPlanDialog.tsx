import {useEffect, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {useTranslation} from 'react-i18next';
import {BookmarkPlus, X} from 'lucide-react';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import type {SavedPlan} from './savedPlans';

export default function SavedPlanDialog({plan, onSave, onClose}: {
    plan?: SavedPlan; onSave: (name: string, overwrite: boolean) => Promise<void>; onClose: () => void;
}) {
    const {t} = useTranslation('main');
    const [name, setName] = useState(plan?.name ?? '');
    const [busy, setBusy] = useState(false);
    const [failed, setFailed] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    useEffect(() => {
        const previous = document.activeElement as HTMLElement | null;
        inputRef.current?.focus(); inputRef.current?.select();
        return () => previous?.focus();
    }, []);
    const save = async (overwrite: boolean) => {
        setBusy(true); setFailed(false);
        try { await onSave(name.trim(), overwrite); onClose(); }
        catch { setFailed(true); }
        finally { setBusy(false); }
    };
    return createPortal(<ModalOverlay className="wealth-plan-overlay" onClose={busy ? undefined : onClose} closeOnBackdrop={!busy} captureEscape aria-labelledby="wealth-save-title">
        <form className="wealth-plan-dialog" onSubmit={event => {event.preventDefault(); void save(Boolean(plan));}}>
            <header><BookmarkPlus size={20}/><h3 id="wealth-save-title">{t('calcStudio.savePlan')}</h3><button type="button" className="titlebar-btn" disabled={busy} onClick={onClose} aria-label={t('windowControls.close')}><X size={18}/></button></header>
            <div className="calc-studio-fields"><div className="calc-studio-field calc-studio-full-row">
                <label htmlFor="wealth-plan-name">{t('calcStudio.planName')}</label>
                <input ref={inputRef} id="wealth-plan-name" value={name} maxLength={80} required disabled={busy} onChange={event => setName(event.target.value)}/>
            </div></div>
            {failed && <p className="calc-studio-error" role="alert">{t('calcStudio.planError')}</p>}
            <div className="modal-action-footer">
                <button type="button" className="modal-action-cancel" disabled={busy} onClick={onClose}>{t('calcStudio.cancelPlan')}</button>
                {plan && <button type="button" className="modal-action-cancel" disabled={busy || !name.trim()} onClick={() => void save(false)}>{t('calcStudio.saveCopy')}</button>}
                <button type="submit" className="modal-action-submit" disabled={busy || !name.trim()}>{t(busy ? 'calcStudio.savingPlan' : plan ? 'calcStudio.updatePlan' : 'calcStudio.savePlan')}</button>
            </div>
        </form>
    </ModalOverlay>, document.body);
}
