import {useTranslation} from 'react-i18next';
import type {SettingsSaveState} from './useSettingsSaveFeedback';

export default function SettingsSaveButton({state, disabled, onClick}: {
    state: SettingsSaveState;
    disabled?: boolean;
    onClick: () => void;
}) {
    const {t} = useTranslation('settings');
    return <button
        className={`mcp-btn-primary${state === 'saved' ? ' is-saved' : state === 'failed' ? ' is-failed' : ''}`}
        onClick={onClick} disabled={disabled || state === 'saving'} aria-live="polite">
        {state === 'saving' ? t('common:saving')
            : state === 'saved' ? `✓ ${t('apiKeyField.savedMsg')}`
                : state === 'failed' ? t('mcp.saveFailed') : t('mcp.save')}
    </button>;
}
