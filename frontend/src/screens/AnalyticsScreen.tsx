import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { api } from '@/lib/api';

interface ExpenseAnalytics { summary: { total_minor: number; base_currency: string; categories: { category: string; total_minor: number }[] }; daily: { day: string; value: number }[] }
interface Productivity { completion_percent: number; captures_total: number; captures_failed: number; captures_undone: number }

export function AnalyticsScreen(): JSX.Element {
  const expenses = useQuery({ queryKey: ['analytics', 'expenses'], queryFn: () => api.get<ExpenseAnalytics>('/analytics/expenses') });
  const productivity = useQuery({ queryKey: ['analytics', 'productivity'], queryFn: () => api.get<Productivity>('/analytics/productivity') });
  if (expenses.isLoading || productivity.isLoading) return <section className="p-4"><div className="od-skeleton h-8 w-28" /><div className="od-skeleton mt-5 h-52" /></section>;
  if (expenses.isError || productivity.isError) return <section className="p-4"><ErrorCard message="Could not load analytics." retry={() => { void expenses.refetch(); void productivity.refetch(); }} /></section>;
  return <section className="p-4"><ScreenHeader title="Analytics" />{expenses.data.daily.some(point => point.value > 0) ? <div className="od-card"><p className="mb-3 font-medium">Expenses</p><div className="h-48"><ResponsiveContainer width="100%" height="100%"><BarChart data={expenses.data.daily}><XAxis dataKey="day" hide /><YAxis hide /><Bar dataKey="value" fill="var(--od-accent)" radius={4} /></BarChart></ResponsiveContainer></div><p className="mt-3 text-sm text-ink-muted">{expenses.data.summary.total_minor / 100} {expenses.data.summary.base_currency}</p></div> : <EmptyCard>Not enough data yet.</EmptyCard>}<div className="mt-4 grid grid-cols-2 gap-3"><div className="od-card"><p className="text-sm text-ink-muted">Productivity</p><p className="mt-1 text-2xl font-semibold">{productivity.data.completion_percent}%</p></div><div className="od-card"><p className="text-sm text-ink-muted">Captures</p><p className="mt-1 text-2xl font-semibold">{productivity.data.captures_total}</p></div></div></section>;
}
