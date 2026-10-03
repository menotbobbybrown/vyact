import {useTranslation} from 'react-i18next';
import ModalTabs from '../ModalTabs/ModalTabs';

export type ModelRole = 'llm' | 'jev';

export default function ModelRoleTabs({role, onChange, disabled}: {
    role: ModelRole; onChange: (role: ModelRole) => void; disabled?: boolean;
}) {
    const {t} = useTranslation('main');
    return <ModalTabs tabs={[
        {key: 'llm' as const, label: t('decisionModels.llm')},
        {key: 'jev' as const, label: t('decisionModels.jev')},
    ]} activeKey={role} onChange={onChange} disabled={disabled}/>;
}
