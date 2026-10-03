import OverflowTooltipText from '../common/OverflowTooltipText/OverflowTooltipText';
import ModelCapabilityIcons from '../common/ModelCapabilityIcons/ModelCapabilityIcons';
import React, {useState} from 'react';
import {Ellipsis, Pencil, Settings, Trash2} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import CustomSelect from '../CustomSelect/CustomSelect';
import type {SelectOption} from '../CustomSelect/CustomSelect';
import ConfirmModal from '../common/ConfirmModal/ConfirmModal';
import ActionMenu from '../common/ActionMenu/ActionMenu';
import ModelRoleTabs, {type ModelRole} from '../common/ModelRoleTabs/ModelRoleTabs';
import './ModelSelector.css';

interface ModelSelectorProps {
    decisionInstalled: string[];
    decisionModel: string;
    onDecisionModelChange: (model: string) => Promise<void>;
    onDecisionSettingsOpen: (model: string) => void;
    installed: string[];
    mtpSupported: string[];
    mtpActive: string | null;
    dflash2Supported: string[];
    dflash2Active: string | null;
    visionSupported: string[];
    audioSupported: string[];
    selectedModel: string;
    currentProvider: string;
    disabled?: boolean;
    onModelChange: (model: string, needsDownload: boolean, modelType?: ModelType) => void;
    onModelDelete: (model: string) => Promise<void>;
    onModelSettingsOpen: (model: string) => void;
    onProviderSettingsOpen: (role?: ModelRole) => void;
}

type ModelType = 'chat' | 'image_gen' | 'image_edit';

const getModelDisplayName = (modelId: string) => modelId.split('/').filter(Boolean).pop() || modelId;

const ModelSelector: React.FC<ModelSelectorProps> = ({
                                                         decisionInstalled, decisionModel, onDecisionModelChange, onDecisionSettingsOpen,
                                                         installed,
                                                         mtpSupported,
                                                         mtpActive,
                                                         dflash2Supported,
                                                         dflash2Active,
                                                         visionSupported,
                                                         audioSupported,
                                                         selectedModel,
                                                         currentProvider,
                                                         disabled = false,
                                                         onModelChange,
                                                         onModelDelete,
                                                         onModelSettingsOpen,
                                                         onProviderSettingsOpen,
                                                     }) => {
    const {t} = useTranslation('main');
    const [role, setRole] = useState<ModelRole>('llm');
    const activeSelection = role === 'jev' ? decisionModel : selectedModel;
    const [modelToDelete, setModelToDelete] = useState<string | null>(null);
    const [modelMenuOpen, setModelMenuOpen] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const handleLocalModelSelect = (model: string, modelType?: ModelType) => {
        const needsDownload = !installed.includes(model);
        onModelChange(model, needsDownload, modelType);
    };

    const allModelIds = role === 'jev' ? decisionInstalled : installed.filter(id => !decisionInstalled.includes(id));
    const options: SelectOption[] = allModelIds.map(id => {
        return {value: id, label: getModelDisplayName(id)};
    });

    if (role === 'jev') options.unshift({value: '', label: t('decisionModels.disabled')});

    // 트리거: dot + 모델명
    const renderTrigger = (_label: string, open: boolean) => {
        const isInstalled = installed.includes(selectedModel);
        const showMtp = currentProvider === 'vyact' && mtpActive === selectedModel;
        const showDFlash2 = currentProvider === 'vyact' && dflash2Active === selectedModel;
        const supportsVision = currentProvider === 'vyact' && visionSupported.includes(selectedModel);
        const supportsAudio = currentProvider === 'vyact' && audioSupported.includes(selectedModel);
        return (
            <>
                <div className={`mdot ${isInstalled ? 'installed' : 'not-installed'}`}/>
                {showMtp && <span className="mtp-model-badge">MTP</span>}
                {showDFlash2 && <span className="mtp-model-badge">DFlash2</span>}
                <ModelCapabilityIcons image={supportsVision} audio={supportsAudio}/>
                <OverflowTooltipText as="span" className="mname"
                    text={selectedModel ? getModelDisplayName(selectedModel) : t('modelSelector.selectModel')}/>
                {decisionModel && <span className="decision-model-status" title={getModelDisplayName(decisionModel)}>{t('decisionModels.active')}</span>}
                <span className={`custom-select-arrow${open ? ' open' : ''}`}>▼</span>
            </>
        );
    };

    // 옵션 아이템: dot/체크 + 모델명 + 추천뱃지 + 설치상태
    const renderOption = (opt: SelectOption, isSelected: boolean, closeDropdown: () => void) => {
        if (!opt.value) return <div className="dd-model-disabled-label">{opt.label}</div>;
        const isInst = installed.includes(opt.value);
        const showMtp = currentProvider === 'vyact' && mtpSupported.includes(opt.value);
        const showDFlash2 = currentProvider === 'vyact' && dflash2Supported.includes(opt.value);
        const supportsVision = currentProvider === 'vyact' && visionSupported.includes(opt.value);
        const supportsAudio = currentProvider === 'vyact' && audioSupported.includes(opt.value);

        return (
            <>
                {/* 좌측 선택/dot */}
                <div className="dd-left-icon">
                    {isSelected ? (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                             stroke="var(--accent)" strokeWidth="3">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                    ) : (
                        <div className={`mdot ${isInst ? 'installed' : 'not-installed'}`}/>
                    )}
                </div>

                {/* 실행 경로 및 모델 기능 */}
                <div className="dd-model-badges">
                    {showMtp && <span className="mtp-model-badge">MTP</span>}
                    {showDFlash2 && <span className="mtp-model-badge">DFlash2</span>}
                    <ModelCapabilityIcons image={supportsVision} audio={supportsAudio}/>
                </div>

                {/* 남은 폭 안에서만 표시되는 모델명 */}
                <div className="dd-model-name">
                    <OverflowTooltipText as="span" className="dd-model-label" text={opt.label}/>
                </div>

                {isInst && <ActionMenu
                    isOpen={modelMenuOpen === opt.value}
                    onOpenChange={open => setModelMenuOpen(open ? opt.value : null)}
                    trigger={<Ellipsis size={17} aria-hidden="true"/>}
                    ariaLabel={t('modelSelector.modelActions', {model: opt.label})}
                    className="dd-model-actions"
                    triggerClassName="dd-model-more"
                    menuClassName="dd-model-actions-menu"
                >
                    <button type="button" className="dd-model-action" onClick={() => {setModelMenuOpen(null); closeDropdown(); if (role === 'jev') onDecisionSettingsOpen(opt.value); else onModelSettingsOpen(opt.value);}}><Settings size={15}/>{t(role === 'jev' ? 'decisionModels.settings' : 'modelSettings.title')}</button>
                    {!isSelected && opt.value !== selectedModel && opt.value !== decisionModel && <button type="button" className="dd-model-action danger" onClick={() => {setModelMenuOpen(null); setModelToDelete(opt.value);}}><Trash2 size={15}/>{t('modelSelector.delete')}</button>}
                </ActionMenu>}
            </>
        );
    };

    // 하단 커스텀 모델 입력
    const footer = undefined;

    if (currentProvider !== 'vyact') {
        return (
            <div className="model-select-wrap">
                <div className="cloud-config">
                    <div className="cloud-model-row">
                        <div className="cloud-model-display">
                            <span className="cloud-model-status" aria-hidden="true"/>
                            <span>{selectedModel || t('modelSelector.noModel')}</span>
                        </div>
                        <button className="cloud-model-settings" type="button" disabled={disabled} onClick={() => onProviderSettingsOpen(role)} aria-label={t('modelSelector.settingsManage')}><Pencil size={16}/></button>
                    </div>
                </div>
            </div>
        );
    }

    return (<>
        <CustomSelect
            options={options}
            value={activeSelection}
            header={<ModelRoleTabs role={role} onChange={next => {setRole(next); setModelMenuOpen(null);}}/>}
            onChange={id => role === 'jev' ? void onDecisionModelChange(id) : handleLocalModelSelect(id)}
            searchable
            disabled={disabled}
            searchPlaceholder={t('modelSelector.modelSearch')}
            onOpen={() => setModelMenuOpen(null)}
            searchAction={currentProvider === 'vyact' ? (
                <button
                    type="button"
                    className="custom-select-search-action"
                    aria-label={t('modelSelector.settingsManage')}
                    onClick={() => onProviderSettingsOpen(role)}
                >
                    <Settings size={15} aria-hidden="true"/>
                </button>
            ) : undefined}
            className="model-select-wrap"
            renderTrigger={renderTrigger}
            renderOption={renderOption}
            footer={footer}
        />
        {modelToDelete && <ConfirmModal
            title={t('modelSelector.deleteModelConfirm', {model: getModelDisplayName(modelToDelete)})}
            description={t('modelSelector.deleteModelDescription')}
            options={[
                {label: t('modelSelector.cancel'), value: 'cancel'},
                {label: t('modelSelector.delete'), value: 'delete', variant: 'danger'},
            ]}
            actionLayout="horizontal"
            loading={isDeleting}
            loadingValue="delete"
            loadingLabel={t('modelSelector.deletingModel')}
            onClose={() => setModelToDelete(null)}
            onSelect={value => {
                if (value !== 'delete') {
                    setModelToDelete(null);
                    return;
                }
                setIsDeleting(true);
                void onModelDelete(modelToDelete).catch(() => undefined).finally(() => {
                    setIsDeleting(false);
                    setModelToDelete(null);
                });
            }}
        />}
    </>);
};

export default ModelSelector;
