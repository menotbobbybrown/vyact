import {getVisibleResultColumns} from './resultColumns';
import type {TFunction} from 'i18next';
import {calculateProjection, summarizeProjection, resolveProjectionInputs, profileFields, projectionFields, type ProjectionInputs} from './projection';

export const WEALTH_LAB_PANEL_ID = 'wealth-lab';
export const WEALTH_LAB_CHAT_DRAFT_EVENT = 'vyact:wealth-lab-chat-draft';

export function exportProjectionToChat(inputs: ProjectionInputs, t: TFunction<'main'>): string {
    const resolved = resolveProjectionInputs(inputs);
    const rows = calculateProjection(inputs);
    const last = rows[rows.length - 1];
    const totals = summarizeProjection(rows);
    const columns = getVisibleResultColumns(totals.shortfall > 0).filter(column => column.key !== 'calendarYear' && column.key !== 'age');
    const hasAges = resolved.currentAge !== '';
    return [
        `## ${t('calcStudio.title')}`,
        ...profileFields.filter(key => key !== 'startYear' && (key !== 'currentAge' || inputs.birthYear === '') && inputs[key] !== '').map(key => `- ${t(`calcStudio.${key}`)}: ${inputs[key]}`),
        `- ${t('calcStudio.startYear')}: ${rows[0].calendarYear}`,
        ...projectionFields.map(key => `- ${t(`calcStudio.${key}`)}: ${resolved[key] || '0'}`),
        '', t('calcStudio.timing'), '',
        ...([['balance', last.balance], ['principal', last.principal], ['interest', totals.interest], ['withdrawal', totals.withdrawal], ['totalShortfall', totals.shortfall]] as const)
            .filter(([key]) => key !== 'totalShortfall' || totals.shortfall > 0)
            .map(([key, value]) => `- ${t(`calcStudio.${key}`)}: ${value}`),
        ...(totals.shortfall > 0 && totals.depleted ? [t('calcStudio.depletedAt', {year: totals.depleted.calendarYear, age: totals.depleted.age})] : []),
        '', `### ${t('calcStudio.yearlyResults')}`,
        `| ${[t('calcStudio.year'), t('calcStudio.calendarYear'), ...(hasAges ? [t('calcStudio.age')] : []), ...columns.map(({label}) => t(`calcStudio.${label}`))].join(' | ')} |`,
        `| ${Array.from({length: columns.length + 2 + (hasAges ? 1 : 0)}, () => '---').join(' | ')} |`,
        ...rows.map(row => `| ${[row.year, row.calendarYear, ...(hasAges ? [row.age!] : []), ...columns.map(({key}) => row[key])].map(value => Number(value.toFixed(2))).join(' | ')} |`),
    ].join('\n');
}
