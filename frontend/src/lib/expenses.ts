import { api } from '@/lib/api';

export const EXPENSE_CURRENCIES = ['PLN', 'EUR', 'USD', 'UAH'] as const;
export type ExpenseCurrency = (typeof EXPENSE_CURRENCIES)[number];

export const EXPENSE_CATEGORIES = [
  'food',
  'transport',
  'housing',
  'health',
  'entertainment',
  'shopping',
  'bills',
  'education',
  'travel',
  'other',
] as const;
export type ExpenseCategory = (typeof EXPENSE_CATEGORIES)[number];
export const EXPENSE_PAGE_SIZE = 50;

export interface ExpenseRecord {
  id: string;
  amount_minor: number;
  currency: string;
  base_amount_minor: number | null;
  base_currency: string | null;
  fx_rate: string | null;
  category: string;
  merchant: string | null;
  occurred_at: string;
  description: string | null;
  source_inbox_item_id: string | null;
  created_at: string;
}

export interface ExpensePage {
  items: ExpenseRecord[];
  year: number;
  month: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface CategoryTotal {
  category: string;
  total_minor: number;
  share_percent: number;
}

export interface BudgetSummary {
  currency: string;
  spent_minor: number;
  budget_minor: number | null;
  remaining_minor: number | null;
  usage_percent: number | null;
  warning: boolean;
  exceeded: boolean;
}

export interface MonthlySummary {
  year: number;
  month: number;
  base_currency: string;
  total_minor: number;
  previous_total_minor: number;
  delta_percent: number | null;
  categories: CategoryTotal[];
  budget: BudgetSummary;
}

export interface ExpenseDraft {
  amount_minor: number;
  currency: ExpenseCurrency;
  category: ExpenseCategory;
  merchant?: string | null;
  occurred_at?: string | null;
  description?: string | null;
}

export interface ExpenseChanges {
  amount_minor?: number;
  currency?: ExpenseCurrency;
  category?: ExpenseCategory;
  merchant?: string | null;
}

export interface MonthSelection {
  year: number;
  month: number;
}

function monthQuery(selection: MonthSelection): URLSearchParams {
  return new URLSearchParams({
    year: String(selection.year),
    month: String(selection.month),
  });
}

export function expenseListKey(selection: MonthSelection): (string | number)[] {
  return ['expenses', selection.year, selection.month];
}

export function expenseSummaryKey(selection: MonthSelection): (string | number)[] {
  return ['expenses', 'summary', selection.year, selection.month];
}

export function expensesPath(selection: MonthSelection): string {
  const query = monthQuery(selection);
  query.set('limit', String(EXPENSE_PAGE_SIZE));
  return `/expenses?${query.toString()}`;
}

export function summaryPath(selection: MonthSelection): string {
  return `/expenses/summary?${monthQuery(selection).toString()}`;
}

export function listExpenses(selection: MonthSelection): Promise<ExpensePage> {
  return api.get<ExpensePage>(expensesPath(selection));
}

export function loadSummary(selection: MonthSelection): Promise<MonthlySummary> {
  return api.get<MonthlySummary>(summaryPath(selection));
}

export function createExpense(draft: ExpenseDraft): Promise<ExpenseRecord> {
  return api.post<ExpenseRecord>('/expenses', draft);
}

export function patchExpense(id: string, changes: ExpenseChanges): Promise<ExpenseRecord> {
  return api.patch<ExpenseRecord>(`/expenses/${id}`, changes);
}

export function deleteExpense(id: string): Promise<void> {
  return api.del<void>(`/expenses/${id}`);
}

/** Major units typed by a human become integer minor units for the API. */
export function toMinorUnits(value: string): number | null {
  const parsed = Number(value.replace(',', '.'));
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed * 100);
}

export function fromMinorUnits(minor: number): string {
  return (minor / 100).toFixed(2);
}

export function currentMonth(now = new Date()): MonthSelection {
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}
