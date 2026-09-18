import { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';

import { AppRoutes } from '@/app/routes';
import { AuthGate } from '@/components/AuthGate';
import { LocaleProvider } from '@/i18n/LocaleProvider';
import { initTelegram, type ThemeName } from '@/lib/telegram';

export function App(): JSX.Element {
  const [, setTheme] = useState<ThemeName>('light');

  useEffect(() => initTelegram(setTheme), []);

  return (
    <LocaleProvider>
      <BrowserRouter>
        <AuthGate>
          <AppRoutes />
        </AuthGate>
      </BrowserRouter>
    </LocaleProvider>
  );
}
