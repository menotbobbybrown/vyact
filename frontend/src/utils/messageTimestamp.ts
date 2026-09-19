import i18n from 'i18next';

export function formatTimestamp(timestamp: string, language = i18n.resolvedLanguage || i18n.language || 'en', now = new Date()) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';
  const options: Intl.DateTimeFormatOptions = {hour: '2-digit', minute: '2-digit', hourCycle: 'h23'};
  if (date.toDateString() !== now.toDateString()) {
    options.month = 'numeric';
    options.day = 'numeric';
  }
  return new Intl.DateTimeFormat(language || 'en', options).format(date);
}
