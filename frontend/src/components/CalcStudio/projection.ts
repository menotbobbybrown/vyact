export const MAX_PROJECTION_YEARS = 100;
export const MIN_WITHDRAWAL_YEAR = 2;
export const projectionFields = ['initialAmount', 'annualContribution', 'contributionYears', 'annualWithdrawal', 'withdrawalStartYear', 'annualReturn', 'inflationRate', 'investmentYears'] as const;
export type ProjectionField = typeof projectionFields[number];
export const profileFields = ['profileName', 'currentAge', 'endAge', 'withdrawalAge', 'startYear', 'birthYear'] as const;
export type ProjectionInputs = Record<ProjectionField | typeof profileFields[number], string>;
export const emptyProjection: ProjectionInputs = Object.fromEntries([...projectionFields, ...profileFields].map(key => [key, ''])) as ProjectionInputs;
export const MIN_START_YEAR = 1900;
export const MAX_START_YEAR = 9999 - MAX_PROJECTION_YEARS;

export function createEmptyProjection(): ProjectionInputs {
    return {...emptyProjection, startYear: String(new Date().getFullYear())};
}

export const PROJECTION_STORAGE_KEY = 'vyact:calc-studio';

export function loadProjection(): ProjectionInputs {
    try {
        const saved = JSON.parse(localStorage.getItem(PROJECTION_STORAGE_KEY) || '{}');
        const inputs = Object.fromEntries([...projectionFields, ...profileFields].map(key => [key, typeof saved?.[key] === 'string' ? saved[key] : ''])) as ProjectionInputs;
        if (!inputs.startYear) inputs.startYear = String(new Date().getFullYear());
        if (!inputs.birthYear && inputs.currentAge !== '' && Number.isInteger(Number(inputs.currentAge)) && Number(inputs.currentAge) >= 0) {
            inputs.birthYear = String(Number(inputs.startYear) - Number(inputs.currentAge) - 1);
        }
        if (inputs.withdrawalStartYear && (!Number.isInteger(Number(inputs.withdrawalStartYear)) || Number(inputs.withdrawalStartYear) < MIN_WITHDRAWAL_YEAR)) inputs.withdrawalStartYear = '';
        return inputs;
    } catch { return createEmptyProjection(); }
}

export function resolveProjectionInputs(inputValues: ProjectionInputs): ProjectionInputs {
    let inputs = inputValues;
    if (inputs.birthYear !== '') {
        const birthYear = Number(inputs.birthYear);
        const startYear = Number(inputs.startYear);
        if (!inputs.startYear || !Number.isInteger(birthYear) || birthYear < 1 || birthYear > startYear) throw new Error('invalid');
        inputs = {...inputs, currentAge: String(startYear - birthYear - 1)};
    }
    if (!inputs.currentAge && !inputs.endAge) return inputs;
    const currentAge = Number(inputs.currentAge);
    const endAge = Number(inputs.endAge);
    if (!inputs.currentAge || !inputs.endAge || !Number.isInteger(currentAge) || !Number.isInteger(endAge)
        || currentAge < (inputs.birthYear !== '' ? -1 : 0) || endAge <= currentAge) throw new Error('invalid');
    const withdrawalAge = Number(inputs.withdrawalAge);
    if (inputs.withdrawalAge && (!Number.isInteger(withdrawalAge) || withdrawalAge < currentAge + MIN_WITHDRAWAL_YEAR || withdrawalAge > endAge)) throw new Error('invalid');
    return {...inputs, investmentYears: String(endAge - currentAge), withdrawalStartYear: inputs.withdrawalAge ? String(withdrawalAge - currentAge) : ''};
}

/** Matches Vyvow: withdrawals, contributions (from year two), then annual returns. */
export function calculateProjection(inputValues: ProjectionInputs) {
    const inputs = resolveProjectionInputs(inputValues);
    const startYear = Number(inputs.startYear || new Date().getFullYear());
    if (!Number.isInteger(startYear) || startYear < MIN_START_YEAR || startYear > MAX_START_YEAR) throw new Error('invalid');
    const values = Object.fromEntries(projectionFields.map(key => [key, Number(inputs[key] || 0)])) as Record<ProjectionField, number>;
    if (Object.values(values).some(value => !Number.isFinite(value))) throw new Error('invalid');
    const {initialAmount, annualContribution, contributionYears, annualWithdrawal, withdrawalStartYear, annualReturn, inflationRate, investmentYears} = values;
    if (initialAmount < 0 || annualContribution < 0 || annualWithdrawal < 0 || annualReturn < -100 || annualReturn > 1000 || inflationRate < 0 || inflationRate > 100
        || !Number.isInteger(investmentYears) || investmentYears < 1
        || !Number.isInteger(contributionYears) || contributionYears < 0
        || !Number.isInteger(withdrawalStartYear) || (inputs.withdrawalStartYear !== '' && withdrawalStartYear < MIN_WITHDRAWAL_YEAR)
        || (annualContribution > 0 && contributionYears < 1) || (annualWithdrawal > 0 && withdrawalStartYear < MIN_WITHDRAWAL_YEAR)) throw new Error('invalid');
    let balance = initialAmount;
    let principal = initialAmount;
    let withdrawalAmount = annualWithdrawal;
    return Array.from({length: investmentYears}, (_, index) => {
        const year = index + 1;
        const contribution = year > 1 && year <= contributionYears + 1 ? annualContribution : 0;
        const plannedWithdrawal = withdrawalStartYear > 0 && year >= withdrawalStartYear
            ? (withdrawalAmount *= 1 + inflationRate / 100) : 0;
        const withdrawal = Math.min(balance, plannedWithdrawal);
        const shortfall = plannedWithdrawal - withdrawal;
        balance += contribution - withdrawal;
        const invested = balance;
        const interest = invested === 0 ? 0 : invested * annualReturn / 100;
        balance += interest;
        principal += contribution;
        if (![balance, principal, plannedWithdrawal, shortfall, withdrawal, interest].every(Number.isFinite)) throw new Error('invalid');
        return {year, calendarYear: startYear + year - 1, age: inputs.currentAge !== '' ? Number(inputs.currentAge) + year : undefined, invested, contribution, plannedWithdrawal, withdrawal, shortfall, interest, balance, principal};
    });
}

export function summarizeProjection(rows: ReturnType<typeof calculateProjection>) {
    return {
        interest: rows.reduce((sum, row) => sum + row.interest, 0),
        withdrawal: rows.reduce((sum, row) => sum + row.withdrawal, 0),
        shortfall: rows.reduce((sum, row) => sum + row.shortfall, 0),
        depleted: rows.find(row => row.balance === 0 && (row.withdrawal > 0 || row.shortfall > 0 || row.interest < 0)),
    };
}
