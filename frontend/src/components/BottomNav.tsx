import { NavLink } from 'react-router-dom';

import { useLocale } from '@/i18n/LocaleProvider';

type NavItem = { to: string; label: string; icon: string };
const ITEMS: NavItem[] = [
  { to: '/today', label: 'nav.today', icon: '◉' },
  { to: '/inbox', label: 'nav.inbox', icon: '▤' },
  { to: '/capture', label: 'nav.add', icon: '+' },
  { to: '/analytics', label: 'nav.analytics', icon: '⌁' },
  { to: '/profile', label: 'nav.profile', icon: '◎' },
];

export function BottomNav(): JSX.Element {
  const { t } = useLocale();
  return (
    <nav
      aria-label={t('nav.main')}
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-line bg-surface-raised/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur"
    >
      <div className="mx-auto grid max-w-lg grid-cols-5">
        {ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex min-h-touch flex-col items-center justify-center gap-0.5 py-1 text-xs ${isActive ? 'text-accent' : 'text-ink-muted'}`
            }
            aria-label={t(item.label)}
          >
            <span className={`text-lg leading-none ${item.to === '/capture' ? 'rounded-full bg-accent px-3 py-1 text-accent-ink' : ''}`}>
              {item.icon}
            </span>
            <span>{t(item.label)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
