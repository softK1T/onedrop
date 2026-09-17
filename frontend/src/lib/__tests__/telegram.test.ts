import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  applyTheme,
  detectTheme,
  getInitData,
  getWebApp,
  haptic,
  initTelegram,
  isInsideTelegram,
} from '@/lib/telegram';

interface WebAppStub {
  initData: string;
  colorScheme: 'light' | 'dark';
  themeParams: Record<string, string>;
  isExpanded: boolean;
  ready: ReturnType<typeof vi.fn>;
  expand: ReturnType<typeof vi.fn>;
  onEvent: ReturnType<typeof vi.fn>;
  offEvent: ReturnType<typeof vi.fn>;
  HapticFeedback?: { notificationOccurred: ReturnType<typeof vi.fn> };
}

function stubWebApp(overrides: Partial<WebAppStub> = {}): WebAppStub {
  const app: WebAppStub = {
    initData: 'auth_date=1&hash=abc',
    colorScheme: 'light',
    themeParams: {},
    isExpanded: false,
    ready: vi.fn(),
    expand: vi.fn(),
    onEvent: vi.fn(),
    offEvent: vi.fn(),
    ...overrides,
  };
  window.Telegram = { WebApp: app } as unknown as Window['Telegram'];
  return app;
}

beforeEach(() => {
  delete window.Telegram;
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.style.cssText = '';
});

describe('telegram integration', () => {
  it('reports no web app outside Telegram', () => {
    expect(getWebApp()).toBeNull();
    expect(isInsideTelegram()).toBe(false);
    expect(getInitData()).toBeNull();
  });

  it('exposes signed init data when Telegram provides it', () => {
    stubWebApp({ initData: 'auth_date=2&hash=def' });

    expect(isInsideTelegram()).toBe(true);
    expect(getInitData()).toBe('auth_date=2&hash=def');
  });

  it('treats empty init data as no session', () => {
    stubWebApp({ initData: '' });

    expect(isInsideTelegram()).toBe(false);
    expect(getInitData()).toBeNull();
  });

  it('takes the theme from Telegram when available', () => {
    stubWebApp({ colorScheme: 'dark' });

    expect(detectTheme()).toBe('dark');
  });

  it('falls back to the media query outside Telegram', () => {
    const matchMedia = vi.fn((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }));
    vi.stubGlobal('matchMedia', matchMedia);

    expect(detectTheme()).toBe('dark');
    expect(matchMedia).toHaveBeenCalledWith('(prefers-color-scheme: dark)');
  });

  it('writes the theme name and Telegram colours onto the root element', () => {
    stubWebApp({
      themeParams: {
        bg_color: '#101010',
        secondary_bg_color: '#202020',
        text_color: '#fefefe',
        button_color: '#00a3a3',
      },
    });

    applyTheme('dark');

    const root = document.documentElement;
    expect(root.dataset.theme).toBe('dark');
    expect(root.style.getPropertyValue('--od-surface')).toBe('#202020');
    expect(root.style.getPropertyValue('--od-surface-raised')).toBe('#101010');
    expect(root.style.getPropertyValue('--od-ink')).toBe('#fefefe');
    expect(root.style.getPropertyValue('--od-accent')).toBe('#00a3a3');
  });

  it('keeps defaults when Telegram sends no theme parameters', () => {
    applyTheme('light');

    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.style.getPropertyValue('--od-surface')).toBe('');
  });

  it('marks the app ready, expands it and subscribes to theme changes', () => {
    const app = stubWebApp();
    const onThemeChange = vi.fn();

    const cleanup = initTelegram(onThemeChange);

    expect(app.ready).toHaveBeenCalledTimes(1);
    expect(app.expand).toHaveBeenCalledTimes(1);
    expect(app.onEvent).toHaveBeenCalledWith('themeChanged', expect.any(Function));

    const handler = app.onEvent.mock.calls[0]?.[1] as () => void;
    app.colorScheme = 'dark';
    handler();
    expect(onThemeChange).toHaveBeenCalledWith('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');

    cleanup();
    expect(app.offEvent).toHaveBeenCalledWith('themeChanged', handler);
  });

  it('does not expand an already expanded app', () => {
    const app = stubWebApp({ isExpanded: true });

    initTelegram(vi.fn());

    expect(app.expand).not.toHaveBeenCalled();
  });

  it('still applies a theme when running outside Telegram', () => {
    const cleanup = initTelegram(vi.fn());

    expect(document.documentElement.dataset.theme).toMatch(/light|dark/);
    expect(() => cleanup()).not.toThrow();
  });

  it('sends haptic feedback only when Telegram supports it', () => {
    expect(() => haptic('success')).not.toThrow();

    const notificationOccurred = vi.fn();
    stubWebApp({ HapticFeedback: { notificationOccurred } });
    haptic('error');

    expect(notificationOccurred).toHaveBeenCalledWith('error');
  });
});
