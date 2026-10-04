import {useEffect, useState} from 'react';
import {Cpu, Link2, Pencil, Plus, X} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import {api, type DecisionConnection} from '../../services/api';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import '../ProviderSettingsModal/ProviderSettingsModal.css';
import '../CustomProviderModal/CustomProviderModal.css';
import '../common/ModalOverlay/ModalActions.css';

const NEW_CONNECTION = {name: 'Jev', base_url: 'https://api.typesafe.ai/v1', model: 'jev-latest', api_key: ''};
type ConnectionDraft = typeof NEW_CONNECTION & {id?: string};

export default function DecisionConnectionModal({initialPath, onClose, onSaved, onRefresh}: {
    initialPath?: string; onClose: () => void; onSaved: (path: string) => Promise<void>; onRefresh: () => Promise<void>;
}) {
    const {t} = useTranslation('main');
    const [connections, setConnections] = useState<DecisionConnection[]>([]);
    const [draft, setDraft] = useState<ConnectionDraft | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    useEffect(() => {
        let active = true;
        void api.getDecisionConnections().then(items => {
            if (!active) return;
            setConnections(items);
            const item = items.find(item => item.model_path === initialPath);
            setDraft(item ? {...item, api_key: ''} : items.length ? null : {...NEW_CONNECTION});
        }).catch(() => {if (active) setError(t('decisionModels.loadFailed'));})
            .finally(() => {if (active) setLoading(false);});
        return () => {active = false;};
    }, [initialPath, t]);
    const run = async (action: () => Promise<void>) => {
        setSaving(true); setError('');
        try {await action();} catch {setError(t('decisionModels.loadFailed'));} finally {setSaving(false);}
    };
    return <ModalOverlay className="provider-editor-overlay" onClose={saving ? undefined : onClose} closeOnBackdrop={false}>
        <form role="dialog" aria-modal="true" aria-labelledby="decision-connections-title" className="provider-editor provider-connection-manager" onSubmit={event => {
            event.preventDefault();
            if (!draft) return;
            void run(async () => {
                const connection = await api.saveDecisionConnection(draft);
                await onRefresh();
                await onSaved(connection.model_path);
                onClose();
            });
        }}>
            <header className="provider-editor-header">
                <div className="provider-editor-title-icon"><Link2 size={20}/></div>
                <div><h2 id="decision-connections-title">{t('decisionModels.cloudTitle')}</h2></div>
                <button type="button" className="provider-editor-close" onClick={onClose} disabled={saving} aria-label={t('customProvider.close')}><X size={20}/></button>
            </header>
            {draft ? <div className="provider-connection-list">
                <fieldset className="provider-editor-section" disabled={saving}>
                    <div className="connection-protocol-heading"><span>{t('customProvider.protocol')}</span><a href="https://api.typesafe.ai/docs" target="_blank" rel="noreferrer">TypeSafe System One</a></div>
                    <label className="provider-editor-field"><span>{t('customProvider.name')}</span><input value={draft.name} required maxLength={100} onChange={event => setDraft({...draft, name: event.target.value})}/></label>
                    <label className="provider-editor-field"><span>{t('customProvider.baseUrl')}</span><input type="url" value={draft.base_url} required onChange={event => setDraft({...draft, base_url: event.target.value})}/></label>
                    <label className="provider-editor-field"><span>{t('customProvider.modelId')}</span><input value={draft.model} required onChange={event => setDraft({...draft, model: event.target.value})}/></label>
                    <label className="provider-editor-field"><span>{t('customProvider.apiKey')}</span><input type="password" autoComplete="new-password" value={draft.api_key} required={!draft.id} placeholder={draft.id ? t('decisionModels.keepKey') : undefined} onChange={event => setDraft({...draft, api_key: event.target.value})}/></label>
                </fieldset>
            </div> : <div className="provider-connection-list">
                {connections.map(item => <div className="provider-connection-row" key={item.id}>
                    <div className="provider-connection-details"><div className="provider-connection-summary"><strong>{item.name}</strong><span className="provider-connection-model"><Cpu size={14}/>{item.model}</span></div><span className="provider-connection-url">{item.base_url}</span></div>
                    <button type="button" className="provider-connection-edit" aria-label={`${t('customProvider.edit')} ${item.name}`} onClick={() => setDraft({...item, api_key: ''})}><Pencil size={16}/></button>
                </div>)}
            </div>}
            {error && <p className="model-settings-error" role="alert">{error}</p>}
            <footer className="modal-action-footer">
                {draft?.id && <button type="button" className="modal-action-cancel custom-provider-delete" disabled={saving} onClick={() => void run(async () => {await api.deleteDecisionConnection(draft.id!); await onRefresh(); setConnections(await api.getDecisionConnections()); setDraft(null);})}>{t('modelSelector.delete')}</button>}
                <button type="button" className="modal-action-cancel" disabled={saving} onClick={() => draft && connections.length ? setDraft(null) : onClose()}>{t('customProvider.close')}</button>
                {draft ? <button key="save" type="submit" className="modal-action-submit" disabled={saving || loading}>{t(saving ? 'modelSettings.applying' : 'modelSettings.apply')}</button> : <button key="add" type="button" className="modal-action-submit" disabled={loading || saving} onClick={() => setDraft({...NEW_CONNECTION})}><Plus size={15}/>{t('customProvider.add')}</button>}
            </footer>
        </form>
    </ModalOverlay>;
}
