import { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';

import { AppRoutes } from '@/app/routes';
import { AuthGate } from '@/components/AuthGate';
import { initTelegram, type ThemeName } from '@/lib/telegram';

export function App(): JSX.Element {
  const [, setTheme] = useState<ThemeName>('light');

  useEffect(() => initTelegram(setTheme), []);

  return (
    <BrowserRouter>
      <AuthGate>
        <AppRoutes />
      </AuthGate>
    </BrowserRouter>
  );
}
