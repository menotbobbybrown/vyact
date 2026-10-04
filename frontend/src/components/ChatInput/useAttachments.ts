import {useCallback, useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {isAudioChatFile, isSupportedChatFile} from '../../utils/fileValidation';
import {toast} from '../common/ToastNotifications/ToastNotifications';

// 붙여넣기 텍스트가 글자 수 또는 줄 수 기준을 충족하면 첨부 카드로 처리한다.
const PASTE_MIN_CHARS = 600;
const PASTE_MIN_LINES = 7;
const MAX_FILE_ATTACHMENTS = 10;
const MAX_IMAGE_ATTACHMENTS = 5;

export interface PastedText {
    id: string;
    label: string;  // 첫 줄 또는 앞 30자
    content: string;
}

export interface FileAttachment {
    file: File;
}

export function useAttachments(
    modelType: 'chat' | 'image_gen' | 'image_edit',
    externalDropFiles: File[],
    onExternalDropHandled?: () => void,
    resetTrigger?: number,
    supportsImageInput = true,
    supportsAudioInput = true
) {
    const {t} = useTranslation('main');
    const [images, setImages] = useState<File[]>([]);
    const [fileAttachments, setFileAttachments] = useState<FileAttachment[]>([]);
    const [pastedTexts, setPastedTexts] = useState<PastedText[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const isMediaSupported = useCallback((file: File) => {
        if (file.type.startsWith('image/') && !supportsImageInput) return false;
        if (isAudioChatFile(file) && !supportsAudioInput) return false;
        return true;
    }, [supportsImageInput, supportsAudioInput]);

    const warnUnsupportedMedia = useCallback((files: File[]) => {
        if (files.some(file => file.type.startsWith('image/') && !isMediaSupported(file))) {
            toast.warning(t('fileUpload.imageNotSupported'));
        }
        if (files.some(file => !file.type.startsWith('image/') && !isMediaSupported(file))) {
            toast.warning(t('fileUpload.audioNotSupported'));
        }
    }, [isMediaSupported, t]);

    const filterSupportedFiles = useCallback((selectedFiles: File[]) => {
        const unsupportedFile = selectedFiles.find(file => !isSupportedChatFile(file));
        if (unsupportedFile) {
            toast.warning(t('documentModal.unsupportedFormat', {name: unsupportedFile.name}));
        }
        warnUnsupportedMedia(selectedFiles);
        return selectedFiles.filter(file => isSupportedChatFile(file) && isMediaSupported(file));
    }, [t, isMediaSupported, warnUnsupportedMedia]);

    // 외부 드롭 파일 처리
    useEffect(() => {
        if (externalDropFiles.length > 0 && modelType !== 'image_gen') {
            const supportedFiles = filterSupportedFiles(externalDropFiles);
            const imgs = supportedFiles.filter(f => f.type.startsWith('image/'));
            const files = supportedFiles.filter(f => !f.type.startsWith('image/'));
            if (imgs.length > 0) {
                setImages(prev => [...prev, ...imgs].slice(0, MAX_IMAGE_ATTACHMENTS));
            }
            if (files.length > 0) setFileAttachments(prev => [...prev, ...files.map(f => ({ file: f }))].slice(0, MAX_FILE_ATTACHMENTS));
            onExternalDropHandled?.();
        }
    }, [externalDropFiles, filterSupportedFiles, modelType, onExternalDropHandled]);

    // 대화 전환 시 초기화
    useEffect(() => {
        if (resetTrigger && resetTrigger > 0) {
            setImages([]);
            setFileAttachments([]);
            setPastedTexts([]);
        }
    }, [resetTrigger]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = filterSupportedFiles(Array.from(e.target.files || []));
        const imageFiles = files.filter(f => f.type.startsWith('image/'));
        const otherFiles = files.filter(f => !f.type.startsWith('image/'));
        if (imageFiles.length > 0) {
            setImages(prev => [...prev, ...imageFiles].slice(0, MAX_IMAGE_ATTACHMENTS));
        }
        if (otherFiles.length > 0) setFileAttachments(prev => [...prev, ...otherFiles.map(f => ({ file: f }))].slice(0, MAX_FILE_ATTACHMENTS));
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
        if (modelType === 'image_gen') return;
        const items = e.clipboardData?.items;
        if (!items) return;

        // 이미지 붙여넣기
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                if (file && filterSupportedFiles([file]).length > 0) {
                    setImages(prev => [...prev, file].slice(0, MAX_IMAGE_ATTACHMENTS));
                }
                return;
            }
        }

        // 텍스트 붙여넣기 — 긴 텍스트면 chip으로
        const text = e.clipboardData.getData('text');
        if (text && (text.length >= PASTE_MIN_CHARS || text.split('\n').length >= PASTE_MIN_LINES)) {
            e.preventDefault();
            const firstLine = text.split('\n').find(l => l.trim()) || text;
            const label = firstLine.trim().slice(0, 80) + (firstLine.length > 80 ? '...' : '');
            const id = `paste-${Date.now()}`;
            setPastedTexts(prev => [...prev, { id, label, content: text }]);
        }
    };

    const removePastedText = (id: string) => setPastedTexts(prev => prev.filter(p => p.id !== id));
    const removeImage = (index: number) => {
        setImages(prev => prev.filter((_, i) => i !== index));
    };
    const removeFileAttachment = (index: number) => setFileAttachments(prev => prev.filter((_, i) => i !== index));
    const clearAll = () => { setImages([]); setFileAttachments([]); setPastedTexts([]); };

    const validateAttachments = () => {
        const files = [...images, ...fileAttachments.map(attachment => attachment.file)];
        warnUnsupportedMedia(files);
        return files.every(isMediaSupported);
    };

    return {
        validateAttachments,
        images, fileAttachments, pastedTexts, fileInputRef,
        handleFileSelect, handlePaste,
        removeImage, removeFileAttachment, removePastedText, clearAll,
        setImages, setFileAttachments, setPastedTexts,
    };
}
