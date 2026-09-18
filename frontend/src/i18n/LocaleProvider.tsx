import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { DEFAULT_LOCALE, normaliseLocale, translate, type Locale } from '@/i18n';

const STORAGE_KEY = 'onedrop.locale';

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function telegramLocale(): string | undefined {
  const webApp = window.Telegram?.WebApp as
    | { initDataUnsafe?: { user?: { language_code?: string } } }
    | undefined;
  return webApp?.initDataUnsafe?.user?.language_code;
}

export function resolveLocale(): Locale {
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved) return normaliseLocale(saved);
  const telegram = telegramLocale();
  if (telegram) return normaliseLocale(telegram);
  return normaliseLocale(window.navigator.language || DEFAULT_LOCALE);
}

export function LocaleProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [locale, updateLocale] = useState<Locale>(resolveLocale);
  const setLocale = useCallback((next: Locale): void => {
    window.localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.lang = next;
    updateLocale(next);
  }, []);
  const value = useMemo<LocaleContextValue>(
    () => ({ locale, setLocale, t: (key, values) => translate(locale, key, values) }),
    [locale, setLocale],
  );
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used inside LocaleProvider');
  return value;
}
