import React, {useState} from 'react';
import {Eye, EyeOff, ExternalLink, GripVertical, Link2, Pencil, Plus, Trash2} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import type {CustomProviderPayload, CustomProviderSettings} from '../../services/api';
import {api} from '../../services/api';
import {getCustomProtocolOptions, OPENAI_COMPATIBLE_DOCS_URL} from '../../constants/customProviders';
import CustomSelect from '../CustomSelect/CustomSelect';
import ToggleSwitch from '../common/ToggleSwitch/ToggleSwitch';
import ModalOverlay from '../common/ModalOverlay/ModalOverlay';
import {toast} from '../common/ToastNotifications/ToastNotifications';
import '../ProviderSettingsModal/ProviderSettingsModal.css';
import './CustomProviderModal.css';

interface CustomProviderModalProps {
    connection?: CustomProviderSettings;
    connections?: CustomProviderSettings[];
    onClose: () => void;
    onSave: (selectionType: `custom:${string}`) => Promise<void> | void;
    onDelete?: (selectionType: `custom:${string}`) => Promise<void> | void;
}

interface HeaderRow {
    id: string;
    name: string;
    value: string;
    hasExistingValue: boolean;
    isValueVisible: boolean;
}

const CustomProviderEditor: React.FC<CustomProviderModalProps> = ({connection, onClose, onSave, onDelete}) => {
    const {t} = useTranslation('main');
    const [name, setName] = useState(connection?.name ?? '');
    const [protocol, setProtocol] = useState<'openai-compatible'>(connection?.protocol ?? 'openai-compatible');
    const [baseUrl, setBaseUrl] = useState(connection?.base_url ?? '');
    const [apiKey, setApiKey] = useState('');
    const [isApiKeyVisible, setIsApiKeyVisible] = useState(false);
    const [model, setModel] = useState(connection?.model ?? '');
    const [headers, setHeaders] = useState<HeaderRow[]>(() => (connection?.headers ?? []).map((header, index) => ({
        id: `existing-${index}`,
        name: header.name,
        value: '',
        hasExistingValue: header.has_value,
        isValueVisible: false,
    })));
    const [reasoningEnabled, setReasoningEnabled] = useState(Boolean(connection?.reasoning && connection.reasoning.enabled !== false));
    const [reasoning, setReasoning] = useState(connection?.reasoning ?? {parameter: '', control: 'toggle' as 'toggle' | 'effort', stages: [] as Array<{label: string; value: string}>});
    const [draggedStageIndex, setDraggedStageIndex] = useState<number | null>(null);
    const [dragOverStageIndex, setDragOverStageIndex] = useState<number | null>(null);
    const reorderStage = (from: number, to: number) => {
        if (!reasoningEnabled || saving || from === to) return;
        setReasoning(current => {
            if (from < 0 || to < 0 || from >= current.stages.length || to >= current.stages.length) return current;
            const stages = [...current.stages];
            const [stage] = stages.splice(from, 1);
            stages.splice(to, 0, stage);
            return {...current, stages};
        });
        setDraggedStageIndex(null);
        setDragOverStageIndex(null);
    };
    const [saving, setSaving] = useState(false);

    const addHeader = () => setHeaders(current => [...current, {
        id: `new-${Date.now()}-${current.length}`,
        name: '',
        value: '',
        hasExistingValue: false,
        isValueVisible: false,
    }]);

    const updateHeader = (id: string, field: 'name' | 'value', value: string) => {
        setHeaders(current => current.map(header => header.id === id ? {...header, [field]: value} : header));
    };

    const removeHeader = (id: string) => setHeaders(current => current.filter(header => header.id !== id));

    const toggleHeaderValueVisibility = (id: string) => {
        setHeaders(current => current.map(header => header.id === id
            ? {...header, isValueVisible: !header.isValueVisible}
            : header));
    };

    const handleSave = async () => {
        if (!name.trim() || !baseUrl.trim() || !model.trim()) {
            toast.warning(t('customProvider.validation'));
            return;
        }
        if (headers.some(header => !header.name.trim() || (!header.value.trim() && !header.hasExistingValue))) {
            toast.warning(t('customProvider.headerValidation'));
            return;
        }
        if (reasoningEnabled && (!reasoning.parameter.trim() || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(reasoning.parameter.trim()) || (reasoning.control === 'effort' && (!reasoning.stages.length || reasoning.stages.some(stage => !stage.label.trim() || !stage.value.trim()))))) {
            toast.warning(t('customProvider.reasoningValidation'));
            return;
        }
        setSaving(true);
        try {
            const payload: CustomProviderPayload = {
                name: name.trim(),
                protocol,
                base_url: baseUrl.trim(),
                api_key: apiKey.trim(),
                model: model.trim(),
                reasoning: {...reasoning, enabled: reasoningEnabled, parameter: reasoning.parameter.trim()},
                headers: headers.map(header => ({name: header.name.trim(), value: header.value.trim()})),
            };
            const id = connection
                ? (await api.updateCustomProvider(connection.id, payload), connection.id)
                : (await api.createCustomProvider(payload)).id;
            await api.selectProvider(`custom:${id}`, model.trim());
            await onSave(`custom:${id}`);
            onClose();
        } catch (error) {
            toast.error(t('customProvider.saveFailed'), String(error));
        } finally {
            setSaving(false);
        }
    };

    return <ModalOverlay className="provider-editor-overlay" onClose={onClose} closeOnBackdrop={false}>
        <section className="provider-editor custom-provider-editor" role="dialog" aria-modal="true" aria-labelledby="provider-editor-title" onClick={event => event.stopPropagation()}>
            <header className="provider-editor-header">
                <div className="provider-editor-title-icon"><Link2 size={20}/></div>
                <div><h2 id="provider-editor-title">{connection ? t('customProvider.editTitle') : t('customProvider.addTitle')}</h2></div>
                <button className="provider-editor-close" onClick={onClose} aria-label={t('customProvider.close')}>×</button>
            </header>

            <div className="provider-editor-body">
                <section className="provider-editor-section">
                    <div className="provider-editor-grid">
                        <label className="provider-editor-field"><span>{t('customProvider.name')}</span><input value={name} onChange={event => setName(event.target.value)} placeholder={t('customProvider.namePlaceholder')}/></label>
                        <div className="provider-editor-field"><div className="connection-protocol-heading"><span>{t('customProvider.protocol')}</span><a href={OPENAI_COMPATIBLE_DOCS_URL} target="_blank" rel="noreferrer">{t('customProvider.protocolDocs')}<ExternalLink size={13}/></a></div><CustomSelect options={getCustomProtocolOptions(t)} value={protocol} onChange={value => setProtocol(value as 'openai-compatible')} ariaLabel={t('customProvider.protocol')}/></div>
                    </div>
                    <label className="provider-editor-field"><span>{t('customProvider.baseUrl')}</span><input value={baseUrl} onChange={event => setBaseUrl(event.target.value)} placeholder="http://localhost:8000/v1"/></label>
                    <div className="provider-editor-grid">
                        <label className="provider-editor-field"><span>{t('customProvider.apiKey')}<small>{t('customProvider.optional')}</small></span><div className="provider-api-key-field"><input type={isApiKeyVisible ? 'text' : 'password'} value={apiKey} onChange={event => setApiKey(event.target.value)} placeholder={connection?.has_key ? t('customProvider.apiKeyExisting') : t('customProvider.apiKeyOptional')}/><button type="button" onClick={() => setIsApiKeyVisible(current => !current)} aria-label={t(isApiKeyVisible ? 'customProvider.hideApiKey' : 'customProvider.showApiKey')}>{isApiKeyVisible ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div></label>
                        <label className="provider-editor-field"><span>{t('customProvider.modelId')}</span><input value={model} onChange={event => setModel(event.target.value)} placeholder={t('customProvider.modelPlaceholder')}/></label>
                    </div>
                </section>

                <section className="provider-editor-section connection-reasoning-section">
                    <div className="connection-reasoning-heading"><strong>{t('customProvider.reasoning')}</strong><ToggleSwitch checked={reasoningEnabled} label={t('customProvider.reasoning')} onChange={setReasoningEnabled}/></div>
                    <fieldset disabled={!reasoningEnabled} className="connection-reasoning-fields">
                    <label className="provider-editor-field connection-reasoning-parameter"><span>{t('customProvider.parameter')}</span><input value={reasoning.parameter} onChange={event => setReasoning({...reasoning, parameter: event.target.value})}/></label>
                    <div className="connection-reasoning-modes">{(['toggle', 'effort'] as const).map(control => <label key={control}><input type="radio" name="connection-reasoning-control" checked={reasoning.control === control} onChange={() => setReasoning({...reasoning, control})}/>{t(`customProvider.${control}`)}</label>)}{<button type="button" className={`connection-reasoning-add${reasoning.control !== 'effort' ? ' connection-reasoning-add-hidden' : ''}`} aria-hidden={reasoning.control !== 'effort'} disabled={!reasoningEnabled || reasoning.control !== 'effort'} onClick={() => setReasoning({...reasoning, stages: [...reasoning.stages, {label: '', value: ''}]})}><Plus size={15}/>{t('customProvider.addStage')}</button>}</div>
                    {reasoning.control === 'effort' && <>
                        {reasoning.stages.map((stage, index) => <div className={`connection-reasoning-stage${draggedStageIndex === index ? ' dragging' : ''}${dragOverStageIndex === index ? ' drag-over' : ''}`} key={index}
                            onDragOver={event => { if (draggedStageIndex === null || !reasoningEnabled || saving) return; event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDragOverStageIndex(index === draggedStageIndex ? null : index); }}
                            onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragOverStageIndex(null); }}
                            onDrop={event => { event.preventDefault(); if (draggedStageIndex !== null) reorderStage(draggedStageIndex, index); }}>
                            <button type="button" className="connection-reasoning-drag" draggable={reasoningEnabled && !saving} disabled={!reasoningEnabled || saving} aria-label={t('customProvider.reorderStage')}
                                onDragStart={event => {
                                    event.dataTransfer.effectAllowed = 'move';
                                    event.dataTransfer.setData('text/plain', String(index));
                                    const row = event.currentTarget.parentElement;
                                    if (row) { const bounds = row.getBoundingClientRect(); event.dataTransfer.setDragImage(row, event.clientX - bounds.left, event.clientY - bounds.top); }
                                    setDraggedStageIndex(index);
                                }}
                                onDragEnd={() => { setDraggedStageIndex(null); setDragOverStageIndex(null); }}
                                onKeyDown={event => { if (event.key === 'ArrowUp' || event.key === 'ArrowDown') { event.preventDefault(); reorderStage(index, index + (event.key === 'ArrowUp' ? -1 : 1)); } }}><GripVertical size={15}/></button>
                            <input aria-label={t('customProvider.stageLabel')} placeholder={t('customProvider.stageLabel')} value={stage.label} onChange={event => setReasoning({...reasoning, stages: reasoning.stages.map((item, position) => position === index ? {...item, label: event.target.value} : item)})}/>
                            <input aria-label={t('customProvider.stageValue')} placeholder={t('customProvider.stageValue')} value={stage.value} onChange={event => setReasoning({...reasoning, stages: reasoning.stages.map((item, position) => position === index ? {...item, value: event.target.value} : item)})}/>
                            <button type="button" aria-label={t('customProvider.removeStage')} onClick={() => setReasoning({...reasoning, stages: reasoning.stages.filter((_, position) => position !== index)})}><Trash2 size={15}/></button>
                        </div>)}

                    </>}
                    </fieldset>
                </section>
                <section className="provider-editor-section provider-headers-section">
                    <div className="provider-editor-section-heading provider-headers-heading"><div><strong>{t('customProvider.headers')}</strong><span>{t('customProvider.headersDesc')}</span></div><button type="button" onClick={addHeader}><Plus size={15}/>{t('customProvider.addHeader')}</button></div>
                    {headers.length === 0 ? <button type="button" className="provider-headers-empty" onClick={addHeader}><Plus size={18}/><span>{t('customProvider.noHeaders')}</span></button> : <div className="provider-header-list">
                        <div className="provider-header-labels"><span>{t('customProvider.headerName')}</span><span>{t('customProvider.headerValue')}</span><span/></div>
                        {headers.map(header => <div className="provider-header-row" key={header.id}>
                            <input value={header.name} onChange={event => updateHeader(header.id, 'name', event.target.value)} placeholder="X-API-Key"/>
                            <div className="provider-header-value-field">
                                <input type={header.isValueVisible ? 'text' : 'password'} value={header.value} onChange={event => updateHeader(header.id, 'value', event.target.value)} placeholder={header.hasExistingValue ? t('customProvider.headerValueExisting') : t('customProvider.headerValuePlaceholder')}/>
                                <button type="button" onClick={() => toggleHeaderValueVisibility(header.id)} aria-label={t(header.isValueVisible ? 'customProvider.hideHeaderValue' : 'customProvider.showHeaderValue')}>
                                    {header.isValueVisible ? <EyeOff size={16}/> : <Eye size={16}/>}
                                </button>
                            </div>
                            <button type="button" onClick={() => removeHeader(header.id)} aria-label={t('customProvider.removeHeader')}><Trash2 size={16}/></button>
                        </div>)}
                    </div>}
                </section>
            </div>

            <footer className="provider-editor-footer">
                {connection && onDelete && <button className="provider-editor-delete" onClick={() => onDelete(`custom:${connection.id}`)} disabled={saving}>{t('modelSelector.delete')}</button>}
                <button className="provider-editor-cancel" onClick={onClose} disabled={saving}>{t('customProvider.cancel')}</button>
                <button className="provider-editor-save" onClick={handleSave} disabled={saving}>{saving ? t('customProvider.saving') : t('customProvider.save')}</button>
            </footer>
        </section>
    </ModalOverlay>;
};

const CustomProviderModal: React.FC<CustomProviderModalProps> = ({connection, connections = [], onClose, onSave, onDelete}) => {
    const {t} = useTranslation('main');
    const [editor, setEditor] = useState<CustomProviderSettings | 'new' | null>(connection ?? (connections.length ? null : 'new'));
    if (editor) return <CustomProviderEditor
        key={editor === 'new' ? 'new' : editor.id}
        connection={editor === 'new' ? undefined : editor}
        onClose={() => connections.length ? setEditor(null) : onClose()}
        onSave={async selectionType => { await onSave(selectionType); onClose(); }}
        onDelete={onDelete}
    />;
    return <ModalOverlay className="provider-editor-overlay" onClose={onClose} closeOnBackdrop={false}>
        <section className="provider-editor provider-connection-manager" role="dialog" aria-modal="true" aria-labelledby="provider-connections-title">
            <header className="provider-editor-header">
                <div className="provider-editor-title-icon"><Link2 size={20}/></div>
                <div><h2 id="provider-connections-title">{t('customProvider.manageTitle')}</h2></div>
                <button className="provider-editor-close" onClick={onClose} aria-label={t('customProvider.close')}>×</button>
            </header>
            <div className="provider-connection-list">
                {connections.map(item => <div className="provider-connection-row" key={item.id}>
                    <div className="provider-connection-details"><strong>{item.name}</strong><span>{item.model}</span><span>{item.base_url}</span></div>
                    <button className="provider-editor-cancel" onClick={() => setEditor(item)} aria-label={`${t('customProvider.edit')} ${item.name}`}><Pencil size={15}/>{t('customProvider.edit')}</button>
                </div>)}
            </div>
            <footer className="provider-editor-footer">
                <button className="provider-editor-cancel" onClick={onClose}>{t('customProvider.close')}</button>
                <button className="provider-editor-save" onClick={() => setEditor('new')}><Plus size={15}/>{t('customProvider.add')}</button>
            </footer>
        </section>
    </ModalOverlay>;
};

export default CustomProviderModal;
