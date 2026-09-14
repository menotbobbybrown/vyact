import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import ConfirmModal from '../ConfirmModal/ConfirmModal';

export default function ShutdownNotice() {
    const {t} = useTranslation('settings');
    const [reasons, setReasons] = useState<string[] | null>(null);
    useEffect(() => {
        let active = true;
        let receivedEvent = false;
        const unsubscribe = window.ragAPI?.onShutdownBlocked?.(value => {
            receivedEvent = true;
            setReasons(value);
        });
        void window.ragAPI?.getShutdownNotice?.().then(value => {
            if (active && !receivedEvent) setReasons(value);
        });
        return () => { active = false; unsubscribe?.(); };
    }, []);
    const close = () => {
        setReasons(null);
        void window.ragAPI?.dismissShutdownNotice?.();
    };
    if (!reasons) return null;
    return <ConfirmModal
        title={t('general.shutdownBlockedTitle')}
        description={t('general.shutdownBlockedDescription')}
        details={reasons.map(reason => t(`general.shutdownReasons.${reason}`, {
            defaultValue: t('general.shutdownReasons.unavailable'),
        }))}
        options={[{value: 'close', label: t('general.confirm')}]}
        actionLayout="horizontal"
        onSelect={close}
        onClose={close}
    />;
}
