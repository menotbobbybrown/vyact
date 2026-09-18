import {useTranslation} from 'react-i18next';
import {AlertCircle, RefreshCw} from 'lucide-react';
import './WorkspaceLoadError.css';

export default function WorkspaceLoadError({message, onRetry, busy = false}: {
    message: string;
    onRetry: () => void;
    busy?: boolean;
}) {
    const {t} = useTranslation('main');
    return <div className="gwp-load-error" role="alert">
        <AlertCircle aria-hidden="true" size={24}/>
        <strong>{t('networkError.requestFailed')}</strong>
        <p>{message}</p>
        <button type="button" className="gwp-load-error-retry" onClick={onRetry} disabled={busy} aria-label={t('common:retry')} title={t('common:retry')} aria-busy={busy}>
            <RefreshCw aria-hidden="true" size={18} className={busy ? 'gwp-spin' : undefined}/>
        </button>
    </div>;
}
