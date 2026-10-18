import {useEffect, useRef, useState} from 'react';
import {ChartNoAxesCombined, LayoutGrid, Wallet} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import {usePanelManager} from '../../contexts/PanelManagerContext';
import {WEALTH_LAB_PANEL_ID} from '../CalcStudio/chatExport';
import './QuickMenu.css';
import {api} from '../../services/api';
import {HOUSEHOLD_LEDGER_PANEL_ID, VYVOW_TOKEN_CHANGED} from '../../services/vyvow';

export default function QuickMenu({onOpen}: {onOpen: () => void}) {
    const {t} = useTranslation('main');
    const [open, setOpen] = useState(false);
    const panels = usePanelManager();
    const [hasVyvowToken, setHasVyvowToken] = useState(false);
    useEffect(() => {
        let active = true;
        let version = 0;
        const refresh = () => {
            const current = ++version;
            api.getVyvowTokenStatus().then(status => {
                if (active && current === version) {
                    setHasVyvowToken(status.has_token);
                    if (!status.has_token) panels.close(HOUSEHOLD_LEDGER_PANEL_ID);
                }
            }).catch(() => {
                if (active && current === version) {
                    setHasVyvowToken(false);
                    panels.close(HOUSEHOLD_LEDGER_PANEL_ID);
                }
            });
        };
        refresh();
        window.addEventListener(VYVOW_TOKEN_CHANGED, refresh);
        window.addEventListener('focus', refresh);
        return () => {
            active = false;
            window.removeEventListener(VYVOW_TOKEN_CHANGED, refresh);
            window.removeEventListener('focus', refresh);
        };
    }, [open, panels.close]);
    const rootRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const itemRef = useRef<HTMLButtonElement>(null);
    useEffect(() => {
        if (!open) return;
        itemRef.current?.focus();
        const handlePointer = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
        };
        const handleKey = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {event.stopImmediatePropagation(); setOpen(false); triggerRef.current?.focus();}
        };
        document.addEventListener('pointerdown', handlePointer);
        window.addEventListener('keydown', handleKey, true);
        return () => {
            document.removeEventListener('pointerdown', handlePointer);
            window.removeEventListener('keydown', handleKey, true);
        };
    }, [open]);
    return <div className="quick-menu" ref={rootRef} onBlur={event => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
    }}>
        <button ref={triggerRef} className="titlebar-btn" aria-label={t('quickMenu.title')}
            aria-expanded={open} aria-controls={open ? 'titlebar-quick-menu' : undefined} onClick={() => {if (!open) onOpen(); setOpen(!open);}}
            onKeyDown={event => {if (event.key === 'ArrowDown') {event.preventDefault(); onOpen(); setOpen(true);}}}>
            <LayoutGrid size={15}/>
        </button>
        {open && <div className="quick-menu-popover" id="titlebar-quick-menu">
            <button ref={itemRef} className="quick-menu-item" onClick={() => {setOpen(false); triggerRef.current?.focus(); panels.open(WEALTH_LAB_PANEL_ID);}}>
                <ChartNoAxesCombined size={18} aria-hidden="true"/><span>{t('calcStudio.title')}<small>{t('quickMenu.calculatorDescription')}</small></span>
            </button>
            {hasVyvowToken && <button className="quick-menu-item" onClick={() => {
                setOpen(false); triggerRef.current?.focus(); panels.open(HOUSEHOLD_LEDGER_PANEL_ID);
            }}>
                <Wallet size={18} aria-hidden="true"/><span>{t('vyvowLedger.title')}<small>{t('vyvowLedger.description')}</small></span>
            </button>}
        </div>}
    </div>;
}
