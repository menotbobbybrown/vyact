import {useEffect, useRef, useState} from 'react';
import {ChartNoAxesCombined, LayoutGrid} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import {usePanelManager} from '../../contexts/PanelManagerContext';
import {WEALTH_LAB_PANEL_ID} from '../CalcStudio/chatExport';
import './QuickMenu.css';

export default function QuickMenu({onOpen}: {onOpen: () => void}) {
    const {t} = useTranslation('main');
    const [open, setOpen] = useState(false);
    const panels = usePanelManager();
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
        </div>}
    </div>;
}
