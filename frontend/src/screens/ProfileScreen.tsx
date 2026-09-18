import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import type { UserProfile } from '@/app/types';
import { ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { useLocale } from '@/i18n/LocaleProvider';
import { api } from '@/lib/api';

export function ProfileScreen(): JSX.Element {
  const { t } = useLocale();
  const query = useQuery({ queryKey: ['me'], queryFn: () => api.get<UserProfile>('/me') });
  if (query.isLoading) return <section className="p-4"><div className="od-skeleton h-8 w-24" aria-busy="true" /></section>;
  if (query.isError || !query.data) return <section className="p-4"><ErrorCard message={t('profile.loadFailed')} retry={() => void query.refetch()} /></section>;
  const user = query.data;
  const links = [
    ['/settings', t('profile.settings')],
    ['/subscription', t('profile.subscription')],
    ['/privacy', t('profile.privacy')],
    ...(user.is_admin ? [['/admin', t('profile.admin')]] : []),
  ];
  return <section className="p-4">
    <ScreenHeader title={t('profile.title')} />
    <div className="od-card">
      <p className="text-lg font-semibold">{user.first_name ?? t('profile.defaultName')}</p>
      <p className="text-sm text-ink-muted">{user.username ? `@${user.username}` : user.settings.timezone}</p>
    </div>
    <div className="mt-4 space-y-2">{links.map(([to, label]) => <Link className="od-card flex items-center justify-between" to={to} key={to}><span>{label}</span><span className="text-ink-muted" aria-hidden="true">›</span></Link>)}</div>
  </section>;
}
