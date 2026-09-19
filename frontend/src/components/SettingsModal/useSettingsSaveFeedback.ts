import {useEffect, useRef, useState} from 'react';

const SAVE_FEEDBACK_DURATION_MS = 2200;
export type SettingsSaveState = 'idle' | 'saving' | 'saved' | 'failed';

export function useSettingsSaveFeedback() {
    const [saveState, setSaveState] = useState<SettingsSaveState>('idle');
    const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const mounted = useRef(true);
    const clearTimer = () => {
        if (timer.current) clearTimeout(timer.current);
        timer.current = null;
    };
    useEffect(() => {
        mounted.current = true;
        return () => { mounted.current = false; clearTimer(); };
    }, []);
    const resetSaveFeedback = () => { clearTimer(); setSaveState('idle'); };
    const saveWithFeedback = async (save: () => unknown | Promise<unknown>) => {
        clearTimer();
        setSaveState('saving');
        try {
            await save();
            if (mounted.current) setSaveState('saved');
        } catch (error) {
            if (mounted.current) setSaveState('failed');
            throw error;
        } finally {
            if (mounted.current) timer.current = setTimeout(() => setSaveState('idle'), SAVE_FEEDBACK_DURATION_MS);
        }
    };
    return {saveState, resetSaveFeedback, saveWithFeedback};
}
