import { beforeEach, describe, expect, it, vi } from 'vitest';

import { clearTokens, hasSession } from '@/lib/api';
import {
  DEMO_TELEGRAM_ID,
  bootstrapSession,
  loginWithDev,
  loginWithTelegram,
  logout,
} from '@/lib/auth';

type FetchMock = ReturnType<
  typeof vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>
>;

let fetchMock: FetchMock;

function tokenResponse(): Response {
  return new Response(
    JSON.stringify({
      access_token: 'access-1',
      refresh_token: 'refresh-1',
      expires_in: 900,
      token_type: 'bearer',
    }),
    { status: 200, headers: { 'content-type': 'application/json' } },
  );
}

function requestBody(call = 0): Record<string, unknown> {
  const body = fetchMock.mock.calls[call]?.[1]?.body;
  return JSON.parse(String(body)) as Record<string, unknown>;
}

beforeEach(() => {
  clearTokens();
  delete window.Telegram;
  fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();
  vi.stubGlobal('fetch', fetchMock);
});

function stubTelegram(initData: string): void {
  window.Telegram = {
    WebApp: {
      initData,
      colorScheme: 'light',
      themeParams: {},
      isExpanded: true,
      ready: vi.fn(),
      expand: vi.fn(),
      onEvent: vi.fn(),
      offEvent: vi.fn(),
    },
  } as unknown as Window['Telegram'];
}

describe('session bootstrap', () => {
  it('exchanges Telegram init data for a token pair', async () => {
    fetchMock.mockResolvedValueOnce(tokenResponse());

    const mode = await loginWithTelegram('auth_date=1&hash=abc');

    expect(mode).toBe('telegram');
    expect(hasSession()).toBe(true);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/auth/telegram');
    expect(requestBody()).toEqual({ init_data: 'auth_date=1&hash=abc' });
  });

  it('prefers Telegram init data when the Mini App runs inside Telegram', async () => {
    stubTelegram('auth_date=2&hash=def');
    fetchMock.mockResolvedValueOnce(tokenResponse());

    const mode = await bootstrapSession();

    expect(mode).toBe('telegram');
    expect(requestBody()).toEqual({ init_data: 'auth_date=2&hash=def' });
  });

  it('uses the dev login outside Telegram', async () => {
    fetchMock.mockResolvedValueOnce(tokenResponse());

    const mode = await bootstrapSession();

    expect(mode).toBe('dev');
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/auth/dev');
    expect(requestBody()).toEqual({ telegram_user_id: DEMO_TELEGRAM_ID });
  });

  it('returns no mode when Telegram is present but init data is empty', async () => {
    stubTelegram('');
    fetchMock.mockResolvedValueOnce(tokenResponse());

    const mode = await bootstrapSession();

    expect(mode).toBe('dev');
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/auth/dev');
  });

  it('accepts an explicit demo user for the dev login', async () => {
    fetchMock.mockResolvedValueOnce(tokenResponse());

    await loginWithDev(555001);

    expect(requestBody()).toEqual({ telegram_user_id: 555001 });
  });

  it('propagates a failed login and leaves no session behind', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'invalid_init_data' } }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    );

    await expect(loginWithTelegram('broken')).rejects.toThrow();
    expect(hasSession()).toBe(false);
  });

  it('clears the session on logout', async () => {
    fetchMock.mockResolvedValueOnce(tokenResponse());
    await loginWithDev();
    expect(hasSession()).toBe(true);

    await logout();

    expect(hasSession()).toBe(false);
  });
});
