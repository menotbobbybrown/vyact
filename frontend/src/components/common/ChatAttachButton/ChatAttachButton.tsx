import {MessageSquarePlus} from 'lucide-react';
import {useTranslation} from 'react-i18next';
import './ChatAttachButton.css';

export default function ChatAttachButton({onClick, disabled = false}: {onClick: () => void; disabled?: boolean}) {
    const {t} = useTranslation('main');
    return <button type="button" className="chat-attach-button" disabled={disabled} onClick={onClick}>
        <MessageSquarePlus size={15} aria-hidden="true"/>{t('calcStudio.addToChat')}
    </button>;
}
