import {useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {RefreshCw} from 'lucide-react';
import {api} from '../../services/api';
import type {WebSearchCreditSummary, WebSearchUsage} from '../../types';
import WorkspaceSetupGuide from './WorkspaceSetupGuide';
import ApiKeyField from '../common/ApiKeyField/ApiKeyField';
import './WebSearchSettings.css';

export function WebSearchSetupGuide() {
    const {t} = useTranslation('settings');
    return <WorkspaceSetupGuide title={t('webSearch.guideTitle')}>
        <div className="gw-services gw-step-content">{t('webSearch.about')}</div>
        {['signup', 'createKey', 'saveKey'].map((step, index) => <div className="gw-step" key={step}>
            <span className="gw-step-num">{index + 1}</span>
            <div className="gw-step-content">
                {step === 'signup' && <><a href="https://app.tavily.com" target="_blank" rel="noopener noreferrer">{t('webSearch.getKey')}</a>{' — '}</>}
                {t(`webSearch.steps.${step}`)}
            </div>
        </div>)}
        <div className="gw-guide-note">{t('webSearch.freePlan')}</div>
    </WorkspaceSetupGuide>;
}

export function WebSearchCredentials({serverId, hasSavedKey, onSave}: {
    serverId?: string;
    hasSavedKey: boolean;
    onSave: (key: string) => Promise<void>;
}) {
    const [savedRevision, setSavedRevision] = useState(0);
    return <>
        <ApiKeyField allowRemoval hasKey={hasSavedKey} keyPreview="••••••••" onSave={async key => {
            await onSave(key);
            setSavedRevision(value => value + 1);
        }}/>
        <WebSearchUsagePanel serverId={serverId} hasSavedKey={hasSavedKey} savedRevision={savedRevision}/>
    </>;
}

export function WebSearchUsagePanel({serverId, hasSavedKey, savedRevision = 0}: {
    serverId?: string;
    hasSavedKey: boolean;
    savedRevision?: number;
}) {
    const {t, i18n} = useTranslation('settings');
    const [usage, setUsage] = useState<Extract<WebSearchUsage, {status: 'ok'}> | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [refreshIndex, setRefreshIndex] = useState(0);
    const refreshRequested = useRef(false);
    useEffect(() => { setUsage(null); }, [serverId, savedRevision]);
    useEffect(() => {
        let current = true;
        if (!hasSavedKey || !serverId) {
            setUsage(null);
            setError(null);
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        const refresh = refreshRequested.current;
        refreshRequested.current = false;
        api.getWebSearchUsage(serverId, refresh).then(result => {
            if (!current) return;
            if (result.status === 'ok') setUsage(result);
            else setError(result.status);
        }).catch(() => {
            if (current) setError('unavailable');
        }).finally(() => {
            if (current) setLoading(false);
        });
        return () => { current = false; };
    }, [serverId, hasSavedKey, savedRevision, refreshIndex]);

    const formatter = new Intl.NumberFormat(i18n.language);
    const format = (value: number | null | undefined) => value == null ? '—' : formatter.format(value);
    const rows: {label: string; credits: WebSearchCreditSummary | undefined}[] = [
        {label: t('webSearch.plan'), credits: usage?.plan},
    ];
    if (usage && ((usage.paygo.limit ?? 0) > 0 || (usage.paygo.used ?? 0) > 0)) {
        rows.push({label: t('webSearch.paygo'), credits: usage.paygo});
    }
    if (usage && usage.key.limit !== null) rows.push({label: t('webSearch.keyLimit'), credits: usage.key});

    return <section className="web-search-usage" aria-label={t('webSearch.usageTitle')}>
        <div className="web-search-usage-heading">
            <strong>{t('webSearch.usageTitle')}</strong>
            <button type="button" className="mcp-icon-btn" disabled={loading || !hasSavedKey}
                    aria-label={t('webSearch.refresh')} title={t('webSearch.refresh')}
                    onClick={() => { refreshRequested.current = true; setRefreshIndex(value => value + 1); }}>
                <RefreshCw className={loading ? 'web-search-refreshing' : ''} aria-hidden="true"/>
            </button>
        </div>
        {!hasSavedKey ? <p className="mcp-desc">{t('webSearch.saveToView')}</p> : <>
            <table className="web-search-usage-table" aria-busy={loading}>
                <thead><tr><th scope="col">{t('webSearch.scope')}</th><th scope="col">{t('webSearch.limit')}</th><th scope="col">{t('webSearch.used')}</th><th scope="col">{t('webSearch.remaining')}</th></tr></thead>
                <tbody>{rows.map(({label, credits}) => <tr key={label}>
                    <th scope="row">{label}</th><td>{format(credits?.limit)}</td><td>{format(credits?.used)}</td><td>{format(credits?.remaining)}</td>
                </tr>)}</tbody>
            </table>
            <p className="mcp-desc">{t('webSearch.accountNote')}</p>
            {usage?.estimated && <p className="mcp-desc">{t('webSearch.estimatedNote')}</p>}
            {usage?.available === false && <div className="mcp-err" role="status">{t('webSearch.exhausted')}</div>}
            {error && <div className="mcp-err" role="status">{t(`webSearch.errors.${error}`)}</div>}
        </>}
    </section>;
}
