import { useEffect, useState } from 'react';

import { useLocale } from '@/i18n/LocaleProvider';
import { ApiError } from '@/lib/api';
import { bootstrapSession, DEV_LOGIN_ENABLED, loginWithDev } from '@/lib/auth';

type GateState = 'loading' | 'ready' | 'error';

export function AuthGate({ children }: { children: React.ReactNode }): JSX.Element {
  const { t } = useLocale();
  const [state, setState] = useState<GateState>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    void bootstrapSession()
      .then(() => setState('ready'))
      .catch((error: unknown) => {
        setMessage(error instanceof ApiError ? error.message : t('app.authFailed'));
        setState('error');
      });
  }, [t]);

  if (state === 'ready') return <>{children}</>;
  if (state === 'loading') {
    return <main className="flex h-full items-center justify-center p-6" aria-busy="true"><div className="od-card w-full max-w-sm"><div className="od-skeleton h-5 w-40" /><div className="od-skeleton mt-3 h-3 w-full" /></div></main>;
  }
  return (
    <main className="flex h-full items-center justify-center p-6">
      <section className="od-card w-full max-w-sm space-y-4" role="alert">
        <h1 className="text-lg font-semibold">{t('app.authFailed')}</h1>
        <p className="text-sm text-ink-muted">{message}</p>
        {DEV_LOGIN_ENABLED && <button className="od-button-primary w-full" onClick={() => void loginWithDev().then(() => setState('ready')).catch(() => undefined)}>{t('app.devLogin')}</button>}
      </section>
    </main>
  );
}
