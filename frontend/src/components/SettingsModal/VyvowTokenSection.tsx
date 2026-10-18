import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {api} from '../../services/api';
import {saveVyvowToken} from '../../services/vyvow';
import ApiKeyField from '../common/ApiKeyField/ApiKeyField';

export default function VyvowTokenSection() {
    const {t} = useTranslation('settings');
    const [hasToken, setHasToken] = useState<boolean | null>(null);
    const [loadFailed, setLoadFailed] = useState(false);

    useEffect(() => {
        let active = true;
        api.getVyvowTokenStatus().then(status => {
            if (active) setHasToken(status.has_token);
        }).catch(() => { if (active) setLoadFailed(true); });
        return () => { active = false; };
    }, []);

    return <div className="settings-general-section">
        {hasToken === null
            ? <p role="status">{loadFailed ? t('vyvow.loadFailed') : t('common:loading')}</p>
            : <ApiKeyField compact label={t('vyvow.token')} hasKey={hasToken} keyPreview=""
                placeholderEmpty={t('vyvow.placeholder')} allowRemoval
                onSave={async token => {
                    const status = await saveVyvowToken(token);
                    setHasToken(status.has_token);
                }}/>}
    </div>;
}
