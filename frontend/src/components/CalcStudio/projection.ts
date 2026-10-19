export const MAX_PROJECTION_YEARS = 100;
export const MIN_WITHDRAWAL_YEAR = 2;
export const projectionFields = ['initialAmount', 'annualContribution', 'contributionYears', 'annualWithdrawal', 'withdrawalStartYear', 'annualReturn', 'inflationRate', 'investmentYears'] as const;
export type ProjectionField = typeof projectionFields[number];
export const optionalFields = ['monthlyIncome', 'incomeStartAge', 'comparisonReturn1', 'comparisonReturn2'] as const;
export const profileFields = ['profileName', 'currentAge', 'endAge', 'withdrawalAge', 'startYear', 'birthYear'] as const;
export const MAX_INCOME_SOURCES = 20;
export interface IncomeSource {id: string; name: string; monthlyAmount: string; startAge: string; endAge: string}
export type ProjectionInputs = {incomeSources?: IncomeSource[]} & Record<ProjectionField | typeof profileFields[number] | typeof optionalFields[number], string>;
export const emptyProjection: ProjectionInputs = Object.fromEntries([...projectionFields, ...profileFields, ...optionalFields].map(key => [key, ''])) as Omit<ProjectionInputs, 'incomeSources'>;
export function getIncomeSources(inputs: ProjectionInputs): IncomeSource[] {
    if (inputs.incomeSources) return inputs.incomeSources;
    return inputs.monthlyIncome !== '' || inputs.incomeStartAge !== ''
        ? [{id: 'legacy', name: '', monthlyAmount: inputs.monthlyIncome, startAge: inputs.incomeStartAge, endAge: ''}] : [];
}
export function withIncomeSources(inputs: ProjectionInputs, incomeSources = getIncomeSources(inputs)): ProjectionInputs {
    return {...inputs, monthlyIncome: '', incomeStartAge: '', ...(incomeSources.length || inputs.incomeSources ? {incomeSources} : {})};
}
export function incomeSourceError(source: IncomeSource, currentAge: number, endAge: number) {
    if (!source.monthlyAmount) return 'monthlyAmount';
    if (!Number.isFinite(Number(source.monthlyAmount)) || Number(source.monthlyAmount) < 0) return 'monthlyAmount';
    if (!source.startAge || !Number.isInteger(Number(source.startAge)) || Number(source.startAge) < 0 || Number(source.startAge) > endAge) return 'startAge';
    if (source.endAge !== '' && (!Number.isInteger(Number(source.endAge)) || Number(source.endAge) < Math.max(Number(source.startAge), currentAge + 1) || Number(source.endAge) > endAge)) return 'endAge';
    return null;
}
export const MIN_START_YEAR = 1900;
export const MAX_START_YEAR = 9999 - MAX_PROJECTION_YEARS;

export function createEmptyProjection(): ProjectionInputs {
    return {...emptyProjection, startYear: String(new Date().getFullYear())};
}

export const PROJECTION_STORAGE_KEY = 'vyact:calc-studio';

export function loadProjection(): ProjectionInputs {
    try {
        const saved = JSON.parse(localStorage.getItem(PROJECTION_STORAGE_KEY) || '{}');
        const inputs = Object.fromEntries([...projectionFields, ...profileFields, ...optionalFields].map(key => [key, typeof saved?.[key] === 'string' ? saved[key] : ''])) as Omit<ProjectionInputs, 'incomeSources'>;
        if (!inputs.startYear) inputs.startYear = String(new Date().getFullYear());
        if (!inputs.birthYear && inputs.currentAge !== '' && Number.isInteger(Number(inputs.currentAge)) && Number(inputs.currentAge) >= 0) {
            inputs.birthYear = String(Number(inputs.startYear) - Number(inputs.currentAge) - 1);
        }
        if (inputs.withdrawalStartYear && (!Number.isInteger(Number(inputs.withdrawalStartYear)) || Number(inputs.withdrawalStartYear) < MIN_WITHDRAWAL_YEAR)) inputs.withdrawalStartYear = '';
        return withIncomeSources({...inputs, ...(Array.isArray(saved.incomeSources) ? {incomeSources: saved.incomeSources.filter((source: unknown) => source && typeof source === 'object' && ['id', 'name', 'monthlyAmount', 'startAge', 'endAge'].every(key => typeof (source as Record<string, unknown>)[key] === 'string'))} : {})});
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
    const incomeSources = getIncomeSources(inputs);
    if (incomeSources.length > MAX_INCOME_SOURCES || incomeSources.some(source => inputs.currentAge === '' || incomeSourceError(source, Number(inputs.currentAge), Number(inputs.currentAge) + investmentYears))) throw new Error('invalid');
    let balance = initialAmount;
    let principal = initialAmount;
    let withdrawalAmount = annualWithdrawal;
    return Array.from({length: investmentYears}, (_, index) => {
        const year = index + 1;
        const contribution = year > 1 && year <= contributionYears + 1 ? annualContribution : 0;
        const livingExpenses = withdrawalStartYear > 0 && year >= withdrawalStartYear
            ? (withdrawalAmount *= 1 + inflationRate / 100) : 0;
        const age = Number(inputs.currentAge) + year;
        const income = incomeSources.reduce((sum, source) => sum + (age >= Number(source.startAge) && age <= Number(source.endAge || Number(inputs.currentAge) + investmentYears)
            ? Number(source.monthlyAmount) * 12 * (1 + inflationRate / 100) ** index : 0), 0);
        const plannedWithdrawal = Math.max(0, livingExpenses - income);
        const withdrawal = Math.min(balance, plannedWithdrawal);
        const shortfall = plannedWithdrawal - withdrawal;
        balance += contribution - withdrawal;
        const invested = balance;
        const interest = invested === 0 ? 0 : invested * annualReturn / 100;
        balance += interest;
        principal += contribution;
        const presentValue = balance / (1 + inflationRate / 100) ** year;
        if (![income, livingExpenses, presentValue, balance, principal, plannedWithdrawal, shortfall, withdrawal, interest].every(Number.isFinite)) throw new Error('invalid');
        return {income, livingExpenses, presentValue, year, calendarYear: startYear + year - 1, age: inputs.currentAge !== '' ? Number(inputs.currentAge) + year : undefined, invested, contribution, plannedWithdrawal, withdrawal, shortfall, interest, balance, principal};
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

export function calculateScenarios(inputs: ProjectionInputs) {
    const returns = [inputs.annualReturn, inputs.comparisonReturn1, inputs.comparisonReturn2]
        .filter((value, index) => index === 0 || value !== '');
    return [...new Set(returns.map(value => Number(value || 0)))].map(annualReturn => ({
        annualReturn,
        rows: calculateProjection({...inputs, annualReturn: String(annualReturn)}),
    }));
}
