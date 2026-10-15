import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {ArrowDown, ArrowUp, ArrowLeft, ArrowRight, ChevronDown, LockKeyhole, RotateCcw, Plus, Sparkles, UserRound, Trash2, Folder, MessageSquare, GripVertical, ScanSearch} from 'lucide-react';
import ModalTabs from '../../common/ModalTabs/ModalTabs';
import ConfirmModal from '../../common/ConfirmModal/ConfirmModal';
import {canExcludePrompt, excludeAllPrompts, normalizeSelectedPrompts, createDefaultPromptDraft, sortExcludedPrompts, getPromptDefinition, loadPromptDraft, type PromptDraft, type PromptScope} from './promptProcessingDraft';
import '../../common/ModalOverlay/ModalActions.css';
import './PromptProcessingSection.css';
import {fetchPromptSettings, persistPromptSettings} from './promptProcessingApi';
import {usePromptDrag} from './usePromptDrag';

export default function PromptProcessingSection() {
    const {t} = useTranslation('settings');
    const [drafts, setDrafts] = useState(loadPromptDraft);
    const [savedDrafts, setSavedDrafts] = useState(drafts);
    const hasChanges = JSON.stringify(drafts) !== JSON.stringify(savedDrafts);
    const [scope, setScope] = useState<PromptScope>('general');
    const [pendingScope, setPendingScope] = useState<PromptScope | null>(null);
    const draft = drafts[scope];
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [confirm, setConfirm] = useState<string | null>(null);
    const [storageFailed, setStorageFailed] = useState(false);
    const [loading, setLoading] = useState(true);
    const [loadFailed, setLoadFailed] = useState(false);
    const [saving, setSaving] = useState(false);
    useEffect(() => {
        let active = true;
        fetchPromptSettings().then(result => {
            if (active) {setDrafts(result.drafts); setSavedDrafts(result.saved);}
        }).catch(() => {if (active) setLoadFailed(true);})
            .finally(() => {if (active) setLoading(false);});
        return () => {active = false;};
    }, []);
    const included = draft.filter(item => item.enabled);
    const excluded = sortExcludedPrompts(draft);
    const titleFor = (item: PromptDraft) => item.title ?? (item.source === 'user' ? t('promptProcessing.customTitle') : t(`promptProcessing.items.${item.id}.title`));
    const updateDraft = (next: PromptDraft[]) => {
        const nextDrafts = {...drafts, [scope]: normalizeSelectedPrompts(next)};
        setDrafts(nextDrafts);
        setStorageFailed(false);
    };
    const handleSave = async () => {
        setSaving(true);
        try {
            const saved = await persistPromptSettings(drafts);
            setDrafts(saved);
            setSavedDrafts(saved);
            setStorageFailed(false);
            return true;
        } catch {
            setStorageFailed(true);
            return false;
        } finally {setSaving(false);}
    };
    const handleCancel = () => {
        setDrafts(savedDrafts);
        setExpandedId(null);
        setConfirm(null);
        setStorageFailed(false);
        drag.finish();
    };
    const drag = usePromptDrag(draft, updateDraft);
    const changeScope = (next: PromptScope) => {
        setScope(next);
        setExpandedId(null);
        setConfirm(null);
        setPendingScope(null);
        setStorageFailed(false);
        drag.finish();
    };
    const requestScopeChange = (next: PromptScope) => {
        if (next === scope) return;
        if (hasChanges) setPendingScope(next);
        else changeScope(next);
    };
    const updateItem = (id: string, change: Partial<PromptDraft>) => {
        updateDraft(draft.map(item => item.id === id ? {...item, ...change} : item));
    };
    const moveItem = (index: number, direction: number) => {
        const next = [...included];
        const destination = index + direction;
        if (destination < 0 || destination >= next.length) return;
        [next[index], next[destination]] = [next[destination], next[index]];
        updateDraft([...next, ...excluded]);
    };
    const confirmAction = () => {
        updateDraft(confirm === 'all'
            ? [...createDefaultPromptDraft(scope), ...draft.filter(item => item.source === 'user').map(item => ({...item, enabled: false}))]
            : draft.flatMap(item => item.id !== confirm ? [item] : item.source === 'user' ? [] : [{...item, enabled: false}]));
        setExpandedId(null);
        setConfirm(null);
    };

    const renderItem = (item: PromptDraft, index: number) => {

        const definition = getPromptDefinition(item.id);
        const isUser = item.source === 'user';
        const editable = isUser || !!definition && 'editable' in definition;
        const expanded = editable && expandedId === item.id;
        const ItemContent = editable ? 'button' : 'div';
        const searchConditional = definition && 'searchConditional' in definition && definition.searchConditional;
        const title = titleFor(item);
        return <li key={item.id} className={`prompt-processing-item${item.enabled ? '' : ' is-disabled'}${isUser ? ' is-user' : ''}${drag.draggedId === item.id ? ' dragging' : ''}${drag.targetId === item.id ? ' drag-over' : ''}`}
            onDragOver={event => drag.over(event, item.enabled, item.id)}
            onDrop={event => drag.drop(event, item.enabled, item.id)}>
            <div className="prompt-processing-row">
                <button className="prompt-processing-grip" draggable onDragStart={event => drag.start(event, item.id)}
                    onDragEnd={drag.finish} aria-label={t('promptProcessing.drag', {title})}>
                    <GripVertical size={16}/></button>
                <ItemContent className={`prompt-processing-expand${editable ? '' : ' is-readonly'}`} aria-expanded={editable ? expanded : undefined}
                        aria-controls={editable ? `prompt-preview-${item.id}` : undefined}
                        onClick={editable ? () => setExpandedId(expanded ? null : item.id) : undefined}>
                    <span className="prompt-processing-item-heading">
                        <span className={`prompt-processing-source${isUser ? ' is-user' : ''}`}
                            role="img" aria-label={t(isUser ? 'promptProcessing.userSource' : 'promptProcessing.vyactSource')}>
                            {isUser ? <UserRound size={13}/> : <Sparkles size={13}/>}
                        </span>
                        <strong>{title}</strong>
                        {!editable && <span className="prompt-processing-lock" role="img" aria-label={t('promptProcessing.automatic')}><LockKeyhole size={12}/></span>}
                        {searchConditional && <span className="prompt-processing-conditional" role="img" aria-label={t('promptProcessing.searchConditional')}><ScanSearch size={12} strokeWidth={1.8}/></span>}
                    </span>
                    <span className="prompt-processing-description">{isUser ? (item.content?.trim() || t('promptProcessing.customDescription')) : t(`promptProcessing.items.${item.id}.description`)}</span>
                    {editable && <ChevronDown size={14} className={expanded ? 'is-expanded' : ''}/>}
                </ItemContent>
                <div className="prompt-processing-actions">
                    {canExcludePrompt(item.id) && <button className="prompt-processing-icon"
                        aria-label={t(item.enabled ? 'promptProcessing.exclude' : 'promptProcessing.include', {title})}
                        onClick={() => updateItem(item.id, {enabled: !item.enabled})}>
                        {item.enabled ? <ArrowLeft size={15}/> : <ArrowRight size={15}/>}</button>}
                    {item.enabled && <>
                        <button className="prompt-processing-icon"
                            aria-label={t('promptProcessing.moveUp', {title})} disabled={index === 0} onClick={() => moveItem(index, -1)}><ArrowUp size={15}/></button>
                        <button className="prompt-processing-icon"
                            aria-label={t('promptProcessing.moveDown', {title})} disabled={index === included.length - 1} onClick={() => moveItem(index, 1)}><ArrowDown size={15}/></button>
                    </>}
                </div>
            </div>
            {expanded && <div id={`prompt-preview-${item.id}`} className="prompt-processing-editor">
                <>
                    <label>{t('promptProcessing.title')}<input value={title} maxLength={120}
                        onChange={event => updateItem(item.id, {title: event.target.value})}/></label>
                    <label>{t('promptProcessing.content')}<textarea rows={9} value={item.content ?? (definition && 'editable' in definition ? t(`promptProcessing.defaults.${item.id}`) : '')}
                        onChange={event => updateItem(item.id, {content: event.target.value})}/></label>
                    {!isUser && <p className="prompt-processing-hint">{t('promptProcessing.originalNotice')}</p>}
                    <div className="prompt-processing-editor-actions">
                        {!isUser && <button className="modal-action-cancel" onClick={() => updateItem(item.id, {title: undefined, content: undefined})}>
                            <RotateCcw size={14}/>{t('promptProcessing.restoreItem')}</button>}
                        {(item.enabled || isUser) && <button className="prompt-processing-remove" onClick={() => setConfirm(item.id)}>
                            {isUser ? <Trash2 size={14}/> : <ArrowLeft size={14}/>}
                            {t(isUser ? 'promptProcessing.deleteCustom' : 'promptProcessing.remove')}</button>}
                    </div>
                </>
            </div>}
        </li>;
    };

    if (loading) return <p className="prompt-processing-hint">{t('common:loading')}</p>;
    if (loadFailed) return <p role="alert" className="prompt-processing-error">{t('promptProcessing.loadFailed')}</p>;
    return <section className="prompt-processing">
        <div className="prompt-processing-header">
            <h3>{t('tabs.promptProcessing')}</h3>
            <div className="prompt-processing-toolbar">
            <button className="modal-action-submit" onClick={() => {
                const item: PromptDraft = {id: `custom:${crypto.randomUUID()}`, source: 'user', createdOrder: Math.max(-1, ...draft.filter(item => item.source === 'user').map(item => item.createdOrder ?? 0)) + 1, title: t('promptProcessing.customTitle'), content: '', enabled: false};
                updateDraft([...draft, item]);
                setExpandedId(item.id);
            }}><Plus size={14}/>{t('promptProcessing.addCustom')}</button>
            <button className="modal-action-cancel" onClick={() => setConfirm('all')}>
                <RotateCcw size={14}/>{t('promptProcessing.restoreAll')}
            </button>
            </div>
        </div>
        <ModalTabs disabled={saving} activeKey={scope} onChange={requestScopeChange}
            tabs={[{key: 'general', label: <><MessageSquare size={14}/>{t('promptProcessing.generalTab')}</>},
                {key: 'project', label: <><Folder size={14}/>{t('promptProcessing.projectTab')}</>}]} />
        <div className="prompt-processing-guidance">
        <p className="prompt-processing-hint">{t(scope === 'general' ? 'promptProcessing.generalHint' : 'promptProcessing.projectHint')}</p>
        {hasChanges && <div className="prompt-processing-save-actions">
            <button className="modal-action-cancel" disabled={saving} onClick={handleCancel}>{t('common:cancel')}</button>
            <button className="modal-action-submit" disabled={saving} onClick={() => void handleSave()}>{t(saving ? 'common:saving' : 'common:save')}</button>
        </div>}
        </div>
        {storageFailed && <p role="alert" className="prompt-processing-error">{t('promptProcessing.storageFailed')}</p>}
        <div className="prompt-processing-columns">
            {[{id: 'excluded', items: excluded}, {id: 'included', items: included}].map(column =>
                <section key={column.id} className="prompt-processing-column" aria-labelledby={`prompt-column-${column.id}`}>
                    <div className="prompt-processing-column-header">
                        <h4 id={`prompt-column-${column.id}`}>{t(`promptProcessing.${column.id}`)} <span>{column.items.length + (column.id === 'included' ? 1 : 0)}</span></h4>
                        {column.id === 'included' && <button className="modal-action-cancel prompt-processing-exclude-all"
                            disabled={!included.some(item => canExcludePrompt(item.id))} onClick={() => {
                                updateDraft(excludeAllPrompts(draft));
                                setExpandedId(null);
                                drag.finish();
                            }}><ArrowLeft size={14}/>{t('promptProcessing.excludeAll')}</button>}
                    </div>
                    <ol className={`prompt-processing-list${column.items.length ? '' : ' is-empty'}${drag.targetId === column.id ? ' drag-over' : ''}`} tabIndex={0} aria-label={t(`promptProcessing.${column.id}`)}
                        onDragOver={event => drag.over(event, column.id === 'included')}
                        onDrop={event => drag.drop(event, column.id === 'included')}>
                        {column.items.map(renderItem)}
                        {!column.items.length && <li className="prompt-processing-empty">{t(`promptProcessing.${column.id}Empty`)}</li>}
                    </ol>
                    {column.id === 'included' && <div className="prompt-processing-user-input">
                        <div className="prompt-processing-user-input-title">
                            <UserRound size={18} aria-hidden="true"/>
                            <strong>{t('promptProcessing.userInputTitle')}</strong>
                            <span className="prompt-processing-user-input-lock" role="img" aria-label={t('promptProcessing.automatic')}><LockKeyhole size={12}/></span>
                        </div>
                        <p>{t('promptProcessing.userInputDescription')}</p>
                    </div>}
                </section>)}
        </div>
        {pendingScope && <ConfirmModal className="unsaved-changes-dialog" actionLayout="horizontal"
            title={t('main:googleWorkspace.unsavedSettings')}
            description={storageFailed ? t('promptProcessing.storageFailed') : t('main:googleWorkspace.unsavedSettingsDescription')}
            options={[
                {label: t('main:googleWorkspace.keepEditing'), value: 'stay'},
                {label: t('main:googleWorkspace.discardAndLeave'), value: 'discard'},
                {label: t('main:googleWorkspace.saveAndLeave'), value: 'save', variant: 'primary'},
            ]}
            onClose={() => setPendingScope(null)}
            loading={saving} loadingValue="save"
            onSelect={async value => {
                if (value === 'stay') {setPendingScope(null); return;}
                if (value === 'save' && !await handleSave()) return;
                if (value === 'discard') handleCancel();
                changeScope(pendingScope);
            }}/>}
        {confirm && <ConfirmModal title={t(confirm === 'all' ? 'promptProcessing.restoreAll' : draft.find(item => item.id === confirm)?.source === 'user' ? 'promptProcessing.deleteCustom' : 'promptProcessing.remove')}
            description={t(confirm === 'all' ? 'promptProcessing.restoreScopeConfirm' : draft.find(item => item.id === confirm)?.source === 'user' ? 'promptProcessing.deleteCustomConfirm' : 'promptProcessing.removeConfirm')}
            options={[{label: t('promptProcessing.cancel'), value: 'cancel'},
                {label: t(confirm === 'all' ? 'promptProcessing.restoreAll' : draft.find(item => item.id === confirm)?.source === 'user' ? 'promptProcessing.deleteCustom' : 'promptProcessing.remove'), value: 'confirm', variant: confirm !== 'all' && draft.find(item => item.id === confirm)?.source === 'user' ? 'danger' : 'primary'}]}
            actionLayout="horizontal" onClose={() => setConfirm(null)}
            onSelect={value => value === 'confirm' ? confirmAction() : setConfirm(null)}/>}
    </section>;
}
