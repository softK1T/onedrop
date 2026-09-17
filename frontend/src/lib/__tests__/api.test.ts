import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api, clearTokens, hasSession, setTokens } from '@/lib/api';

type FetchMock = ReturnType<
  typeof vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>
>;

let fetchMock: FetchMock;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function errorResponse(status: number, code: string, message: string): Response {
  return json({ error: { code, message } }, status);
}

function lastInit(call = 0): RequestInit {
  return fetchMock.mock.calls[call]?.[1] ?? {};
}

function headersOf(call = 0): Record<string, string> {
  return (lastInit(call).headers ?? {}) as Record<string, string>;
}

beforeEach(() => {
  clearTokens();
  fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();
  vi.stubGlobal('fetch', fetchMock);
});

describe('api client', () => {
  it('sends a GET without an authorization header when there is no session', async () => {
    fetchMock.mockResolvedValueOnce(json({ items: [] }));

    const result = await api.get<{ items: unknown[] }>('/inbox');

    expect(result).toEqual({ items: [] });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/api/v1/inbox');
    expect(headersOf()).not.toHaveProperty('authorization');
    expect(hasSession()).toBe(false);
  });

  it('attaches the bearer token once a session exists', async () => {
    setTokens('access-1', 'refresh-1');
    fetchMock.mockResolvedValueOnce(json({ ok: true }));

    await api.get('/me');

    expect(hasSession()).toBe(true);
    expect(headersOf().authorization).toBe('Bearer access-1');
  });

  it('sends JSON bodies with a content type', async () => {
    fetchMock.mockResolvedValueOnce(json({ inbox_item_id: 'abc' }));

    await api.post('/capture/text', { text: 'buy milk' });

    expect(lastInit().method).toBe('POST');
    expect(headersOf()['content-type']).toBe('application/json');
    expect(lastInit().body).toBe(JSON.stringify({ text: 'buy milk' }));
  });

  it('uploads form data without forcing a content type', async () => {
    const form = new FormData();
    form.append('file', new Blob(['x']), 'voice.ogg');
    fetchMock.mockResolvedValueOnce(json({ inbox_item_id: 'abc' }));

    await api.upload('/capture/voice', form);

    expect(lastInit().body).toBe(form);
    expect(headersOf()).not.toHaveProperty('content-type');
  });

  it('returns undefined for an empty 204 response', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(api.del('/tasks/1')).resolves.toBeUndefined();
    expect(lastInit().method).toBe('DELETE');
  });

  it('turns an error payload into an ApiError', async () => {
    fetchMock.mockResolvedValueOnce(
      errorResponse(404, 'not_found', 'Task not found'),
    );

    const error = await api.get('/tasks/missing').catch((raised: unknown) => raised);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).code).toBe('not_found');
    expect((error as ApiError).message).toBe('Task not found');
  });

  it('falls back to a synthetic code when the body is not JSON', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('gateway down', { status: 502, statusText: 'Bad Gateway' }),
    );

    const error = (await api
      .get('/dashboard/today')
      .catch((raised: unknown) => raised)) as ApiError;

    expect(error.code).toBe('http_502');
    expect(error.message).toBe('Bad Gateway');
  });

  it('flags quota and plan errors for the paywall', async () => {
    fetchMock.mockResolvedValueOnce(
      errorResponse(402, 'quota_exceeded', 'Daily AI limit reached'),
    );
    const quota = (await api
      .post('/capture/text', { text: 'hi' })
      .catch((raised: unknown) => raised)) as ApiError;

    fetchMock.mockResolvedValueOnce(
      errorResponse(403, 'photo_requires_pro', 'Pro plan required'),
    );
    const pro = (await api
      .post('/capture/image')
      .catch((raised: unknown) => raised)) as ApiError;

    expect(quota.isQuotaExceeded).toBe(true);
    expect(pro.requiresPro).toBe(true);
    expect(pro.isQuotaExceeded).toBe(false);
  });

  it('refreshes the session once and replays the original request', async () => {
    setTokens('expired', 'refresh-1');
    fetchMock
      .mockResolvedValueOnce(errorResponse(401, 'unauthorized', 'Token expired'))
      .mockResolvedValueOnce(
        json({ access_token: 'access-2', refresh_token: 'refresh-2' }),
      )
      .mockResolvedValueOnce(json({ id: 'user-1' }));

    const result = await api.get<{ id: string }>('/me');

    expect(result).toEqual({ id: 'user-1' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('/auth/refresh');
    expect(headersOf(2).authorization).toBe('Bearer access-2');
  });

  it('clears the session when the refresh call is rejected', async () => {
    setTokens('expired', 'refresh-1');
    fetchMock
      .mockResolvedValueOnce(errorResponse(401, 'unauthorized', 'Token expired'))
      .mockResolvedValueOnce(errorResponse(401, 'unauthorized', 'Refresh expired'));

    const error = (await api.get('/me').catch((raised: unknown) => raised)) as ApiError;

    expect(error.isUnauthorized).toBe(true);
    expect(hasSession()).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not try to refresh without a refresh token', async () => {
    fetchMock.mockResolvedValueOnce(errorResponse(401, 'unauthorized', 'No session'));

    await expect(api.get('/me')).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
