export const resultColumns = [
    {key: 'calendarYear', label: 'calendarYear'},
    {key: 'age', label: 'age'},
    {key: 'invested', label: 'invested'},
    {key: 'contribution', label: 'contribution'},
    {key: 'interest', label: 'yearlyInterest'},
    {key: 'plannedWithdrawal', label: 'plannedWithdrawal'},
    {key: 'withdrawal', label: 'actualWithdrawal'},
    {key: 'shortfall', label: 'yearlyShortfall'},
    {key: 'balance', label: 'yearEndBalance'},
] as const;

export function getVisibleResultColumns(hasShortfall: boolean) {
    return resultColumns.filter(column => column.key !== 'shortfall' || hasShortfall);
}
