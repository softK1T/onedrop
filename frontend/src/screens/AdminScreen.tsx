import { useQuery } from '@tanstack/react-query';

import type { AdminOverview } from '@/app/types';
import { ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { useLocale } from '@/i18n/LocaleProvider';
import { ApiError, api } from '@/lib/api';

function Metric({ label, value }: { label: string; value: number }): JSX.Element {
  return <div className="od-card"><p className="text-sm text-ink-muted">{label}</p><p className="mt-1 text-2xl font-semibold">{value.toLocaleString()}</p></div>;
}

export function AdminScreen(): JSX.Element {
  const { t } = useLocale();
  const query = useQuery({ queryKey: ['admin', 'overview'], queryFn: () => api.get<AdminOverview>('/admin/overview'), retry: false });
  if (query.isLoading) return <section className="p-4" aria-busy="true"><ScreenHeader title={t('admin.title')} /><div className="grid grid-cols-2 gap-3"><div className="od-skeleton h-24" /><div className="od-skeleton h-24" /></div></section>;
  if (query.error instanceof ApiError && (query.error.status === 401 || query.error.status === 403)) return <section className="p-4"><ScreenHeader title={t('admin.title')} /><div className="od-card" role="alert">{t('admin.unauthorized')}</div></section>;
  if (query.isError) return <section className="p-4"><ScreenHeader title={t('admin.title')} /><ErrorCard message={t('admin.loadFailed')} retry={() => void query.refetch()} /></section>;
  if (!query.data) return <section className="p-4"><ScreenHeader title={t('admin.title')} /><div className="od-card">{t('admin.empty')}</div></section>;
  const data = query.data;
  return <section className="p-4">
    <ScreenHeader title={t('admin.title')} />
    <div className="grid grid-cols-2 gap-3">
      <Metric label={t('admin.users')} value={data.users_count} />
      <Metric label={t('admin.failedCaptures')} value={data.failed_captures_count} />
      <Metric label={t('admin.pendingNotifications')} value={data.pending_notifications_count} />
      <Metric label={t('admin.failedNotifications')} value={data.failed_notifications_count} />
      <Metric label={t('admin.aiOperations')} value={data.ai_operations_count} />
      <Metric label={t('admin.aiCost')} value={data.ai_cost_micro} />
      <Metric label={t('admin.subscriptions')} value={data.active_subscriptions_count} />
      <Metric label={t('admin.payments')} value={data.payments_count} />
      <Metric label={t('admin.stars')} value={data.payment_stars_total} />
    </div>
    <div className="od-card mt-4">
      <h2 className="font-semibold">{t('admin.captureStatuses')}</h2>
      {Object.keys(data.captures_by_status).length === 0 ? <p className="mt-2 text-sm text-ink-muted">{t('admin.empty')}</p> : <ul className="mt-2 space-y-1">{Object.entries(data.captures_by_status).map(([status, count]) => <li className="flex justify-between" key={status}><span>{status}</span><strong>{count}</strong></li>)}</ul>}
    </div>
  </section>;
}
