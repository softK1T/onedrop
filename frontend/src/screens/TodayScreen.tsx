import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import type { Dashboard } from '@/app/types';
import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { formatMoney, formatTime } from '@/lib/format';
import { api } from '@/lib/api';
import { translate } from '@/i18n';

function Metric({ label, value }: { label: string; value: string | number }): JSX.Element {
  return <div className="od-card"><p className="text-xs text-ink-muted">{label}</p><p className="mt-1 text-xl font-semibold">{value}</p></div>;
}

export function TodayScreen(): JSX.Element {
  const query = useQuery({ queryKey: ['dashboard', 'today'], queryFn: () => api.get<Dashboard>('/dashboard/today') });
  if (query.isLoading) return <section className="p-4" aria-busy="true"><div className="od-skeleton h-8 w-28" /><div className="mt-5 grid grid-cols-2 gap-3"><div className="od-skeleton h-20" /><div className="od-skeleton h-20" /></div></section>;
  if (query.isError) return <section className="p-4"><ErrorCard message="Could not load your dashboard." retry={() => void query.refetch()} /></section>;
  if (!query.data) return <section className="p-4"><EmptyCard>{translate('en', 'today.empty')}</EmptyCard></section>;
  const data = query.data;
  return <section className="p-4"><ScreenHeader title={translate('en', 'today.title')} actionTo="/capture" actionLabel="+" />
    {data.budget_warning && <div className="mb-3 rounded-card bg-warning/15 p-3 text-sm text-warning">{translate('en', 'today.budgetWarning')}</div>}
    <div className="grid grid-cols-2 gap-3"><Metric label={translate('en', 'today.tasks')} value={data.tasks.today} /><Metric label={translate('en', 'today.aiLeft')} value={data.ai.remaining} /><Metric label={translate('en', 'today.spent')} value={formatMoney(data.expenses_today_minor, data.base_currency)} /><Metric label={translate('en', 'today.calories')} value={data.nutrition.calories} /></div>
    <div className="mt-6 space-y-3"><h2 className="font-semibold">{translate('en', 'today.tasks')}</h2>{data.task_items.length ? data.task_items.map(task => <Link to="/tasks" className="od-card block" key={task.id}><p className="font-medium">{task.title}</p><p className="mt-1 text-xs text-ink-muted">{task.priority}{task.due_at ? ` · ${formatTime(task.due_at)}` : ''}</p></Link>) : <EmptyCard>{translate('en', 'today.empty')}</EmptyCard>}</div>
    <div className="mt-6 space-y-3"><h2 className="font-semibold">{translate('en', 'today.events')}</h2>{data.events.length ? data.events.map(event => <Link to="/events" className="od-card block" key={event.id}><p className="font-medium">{event.title}</p><p className="mt-1 text-xs text-ink-muted">{formatTime(event.starts_at)}</p></Link>) : <EmptyCard>{translate('en', 'today.empty')}</EmptyCard>}</div>
  </section>;
}
