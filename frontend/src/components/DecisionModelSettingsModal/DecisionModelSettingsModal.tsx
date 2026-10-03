import {useEffect, useState} from 'react';
import {X} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import {api} from '../../services/api';
import {ApiError} from '../../utils/apiError';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import '../ModelSettingsModal/ModelSettingsModal.css';

export default function DecisionModelSettingsModal({modelPath, onClose, onApplied}: {
    modelPath: string; onClose: () => void; onApplied: () => Promise<void>;
}) {
    const {t} = useTranslation('main');
    const [settings, setSettings] = useState<{model_path: string; context_size: number; timeout_seconds: number} | null>(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    useEffect(() => {
        let active = true;
        void api.getDecisionModel().then(value => {if (active) setSettings({...value, model_path: modelPath});})
            .catch(() => {if (active) setError(t('decisionModels.loadFailed'));});
        return () => {active = false;};
    }, [modelPath, t]);
    return <ModalOverlay className="model-settings-overlay" onClose={saving ? undefined : onClose} closeOnBackdrop={false}>
        <form className="model-settings-modal" onSubmit={event => {
            event.preventDefault();
            if (!settings) return;
            setSaving(true); setError('');
            void api.selectDecisionModel(settings).then(onApplied).then(onClose)
                .catch(error => setError(t(error instanceof ApiError && error.detail === 'decision_model_insufficient_memory' ? 'message.modelInsufficientMemoryTitle' : error instanceof ApiError && error.detail === 'decision_runtime_upgrade_required' ? 'decisionModels.runtimeUpgradeRequired' : 'decisionModels.loadFailed'))).finally(() => setSaving(false));
        }}>
            <header><h2>{t('decisionModels.settings')}</h2><button type="button" onClick={onClose} disabled={saving} aria-label={t('modelSettings.cancel')}><X size={20}/></button></header>
            <div className="model-settings-body">
                <p>{modelPath.split('/').pop()}</p>
                {settings && <>
                    <label className="model-settings-option"><span>{t('modelSettings.context')}</span>
                        <input className="model-settings-input" type="number" min="512" max="32768" required disabled={saving} value={settings.context_size}
                            onChange={event => setSettings({...settings, context_size: Number(event.target.value)})}/></label>

                </>}
                {error && <p className="model-settings-error" role="alert">{error}</p>}
            </div>
            <footer><button className="model-settings-cancel" type="button" disabled={saving} onClick={onClose}>{t('modelSettings.cancel')}</button>
                <button className="primary" type="submit" disabled={!settings || saving}>{t(saving ? 'modelSettings.applying' : 'modelSettings.apply')}</button></footer>
        </form>
    </ModalOverlay>;
}
