import {useId, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {ArrowRight, ChevronDown} from 'lucide-react';
import type {LedgerCurrency, LedgerEntry, LedgerPeriod} from '../../services/vyvow';
import {categoryGroups, convertedAmount, groupEntries, ledgerBalanceClass, ledgerTotals} from './ledgerGroups';
import LedgerMoney from './LedgerMoney';
import LedgerCategoryIcon from './LedgerCategoryIcon';

export default function LedgerTransactionList({groups, period, currency, currencies, onEdit}: {
    groups: [string, LedgerEntry[]][]; period: LedgerPeriod; currency: string; currencies: LedgerCurrency[]; onEdit: (entry: LedgerEntry) => void;
}) {
    const {t, i18n} = useTranslation('main');
    const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
    const idPrefix = useId();
    const money = (amount: number, unit = currency) => <LedgerMoney amount={amount} currency={unit} currencies={currencies}/>;
    const dateText = (value: string, options: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(i18n.language, options).format(new Date(`${value.slice(0, 10)}T12:00:00`));
    const periodLabel = (key: string) => {
        if (key === 'tag') {
            const entries = groups[0][1];
            return [entries[entries.length - 1].createdAt, entries[0].createdAt].map(date => dateText(date, {year: 'numeric', month: 'short', day: 'numeric'})).join(' – ');
        }
        if (period === 'monthly') return dateText(`${key}-01`, {year: 'numeric', month: 'long'});
        if (period === 'daily') return dateText(key, {month: 'short', day: 'numeric', weekday: 'short'});
        const end = new Date(`${key}T12:00:00`);
        end.setDate(end.getDate() + 6);
        return `${dateText(key, {month: 'short', day: 'numeric'})} – ${new Intl.DateTimeFormat(i18n.language, {month: 'short', day: 'numeric'}).format(end)}`;
    };
    const toggle = (keys: string[]) => setExpanded(previous => {
        const next = new Set(previous);
        const close = keys.every(key => previous.has(key));
        keys.forEach(key => close ? next.delete(key) : next.add(key));
        return next;
    });
    const renderEntry = (entry: LedgerEntry, nested = false) => {
        const converted = convertedAmount(entry, currency);
        return <button className={`ledger-entry${nested ? ' ledger-entry--nested' : ''}`} key={entry.id} onClick={() => onEdit(entry)}>
            {!nested && <LedgerCategoryIcon category={entry.houseLedgerOptionId}/>}
            <span className="ledger-entry-description">
                <strong>{nested ? entry.memo || t(`vyvowLedger.categories.op${entry.houseLedgerOptionId}`) : t(`vyvowLedger.categories.op${entry.houseLedgerOptionId}`)}</strong>
                <span>{nested ? '' : entry.memo}{entry.tag && <small>#{entry.tag}</small>}</span>
            </span>
            <span className={`ledger-entry-amount ledger-${entry.txType === 'INCOME' ? 'income' : 'expense'}`}>
                <strong className="ledger-conversion">{money(entry.amount, entry.currency)}{entry.currency !== currency && converted !== null && <><ArrowRight size={13} aria-hidden="true"/>{money(converted)}</>}</strong>
            </span>
        </button>;
    };
    return <div className="ledger-groups">{groups.map(([key, entries]) => {
        const totals = ledgerTotals(entries, currency);
        const categories = categoryGroups(entries, currency);
        const categoryKeys = categories.map(category => `${key}-${category.id}`);
        const allOpen = categoryKeys.every(value => expanded.has(value));
        const heading = <>
            <span className="ledger-group-heading"><strong>{periodLabel(key)}</strong><span className={`ledger-group-net ${ledgerBalanceClass(totals.balance, totals.missing)}`}>{totals.missing ? '—' : money(totals.balance)}</span>{period !== 'daily' && <ChevronDown size={15} className={allOpen ? 'is-expanded' : ''} aria-hidden="true"/>}</span>
            {totals.income > 0 && totals.expense > 0 && <span className="ledger-group-breakdown"><span className="ledger-income">{money(totals.income)}</span><span className="ledger-expense">{money(totals.expense)}</span></span>}
        </>;
        return <section className="ledger-group" key={key}>
            {period === 'daily' ? <div className="ledger-group-header">{heading}</div> : <button className="ledger-group-header" onClick={() => toggle(categoryKeys)} aria-expanded={allOpen} aria-label={`${periodLabel(key)} · ${t(allOpen ? 'vyvowLedger.collapseAll' : 'vyvowLedger.expandAll')}`}>{heading}</button>}
            {period === 'daily' ? entries.map(entry => renderEntry(entry)) : categories.map(category => {
                const categoryKey = `${key}-${category.id}`;
                const isOpen = expanded.has(categoryKey);
                const contentId = `${idPrefix}-${categoryKey}`;
                return <div className="ledger-category" key={category.id}>
                    <button className="ledger-category-toggle" aria-expanded={isOpen} aria-controls={contentId} onClick={() => toggle([categoryKey])}>
                        <LedgerCategoryIcon category={category.id}/>
                        <span className="ledger-category-label"><strong>{t(`vyvowLedger.categories.op${category.id}`)}</strong><small>{t('vyvowLedger.transactionCount', {count: category.entries.length})}</small></span>
                        <strong className={`ledger-${category.type === 'INCOME' ? 'income' : 'expense'}`}>{category.totals.missing ? '—' : money(category.type === 'INCOME' ? category.totals.income : category.totals.expense)}</strong>
                        <ChevronDown size={15} className={isOpen ? 'is-expanded' : ''} aria-hidden="true"/>
                    </button>
                    {isOpen && <div className="ledger-category-children" id={contentId}>{groupEntries(category.entries, 'daily').map(([date, children]) => <div className="ledger-nested-day" key={date}>
                        <div className="ledger-nested-date">{dateText(date, {month: 'short', day: 'numeric', weekday: 'short'})}</div>
                        {children.map(entry => renderEntry(entry, true))}
                    </div>)}</div>}
                </div>;
            })}
        </section>;
    })}</div>;
}
