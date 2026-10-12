import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  ApiError,
  clearSession,
  getToken,
  request,
  saveSession,
  setUnauthorizedHandler,
} from '@/lib/api';

function mockFetch(status: number, payload: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(payload === undefined ? null : JSON.stringify(payload), { status }),
    ),
  );
}

function sentHeaders(): Record<string, string> {
  const [, init] = vi.mocked(fetch).mock.calls[0]!;
  return init?.headers as Record<string, string>;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  clearSession();
  setUnauthorizedHandler(null);
});

describe('request', () => {
  it('returns the parsed JSON body on success', async () => {
    mockFetch(200, { status: 'ok' });
    await expect(request('/health')).resolves.toEqual({ status: 'ok' });
  });

  it('sends JSON bodies with the right content type', async () => {
    mockFetch(200, {});
    await request('/things', { method: 'POST', body: { a: 1 } });

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(init?.method).toBe('POST');
    expect(init?.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(init?.body).toBe('{"a":1}');
  });

  it('sends forms url-encoded', async () => {
    mockFetch(200, {});
    await request('/auth/token', {
      method: 'POST',
      form: new URLSearchParams({ username: 'admin', password: 'pw' }),
      auth: false,
    });

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(sentHeaders()['Content-Type']).toBe('application/x-www-form-urlencoded');
    expect(String(init?.body)).toBe('username=admin&password=pw');
  });

  it('maps backend errors to ApiError', async () => {
    mockFetch(404, { code: 'not_found', message: 'Reservation not found.', details: null });

    const error = await request('/reservations/X').catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 404,
      code: 'not_found',
      message: 'Reservation not found.',
    });
  });

  it('returns undefined for 204 No Content', async () => {
    mockFetch(204, undefined);
    await expect(request('/things/1', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});

describe('auth', () => {
  it('attaches the bearer token when logged in', async () => {
    saveSession('abc', 3600);
    mockFetch(200, []);

    await request('/slots');

    expect(sentHeaders()['Authorization']).toBe('Bearer abc');
  });

  it('does not attach the token when auth is false', async () => {
    saveSession('abc', 3600);
    mockFetch(200, {});

    await request('/auth/token', { method: 'POST', auth: false });

    expect(sentHeaders()['Authorization']).toBeUndefined();
  });

  it('treats an expired session as logged out', () => {
    vi.useFakeTimers();
    saveSession('abc', 60);

    vi.advanceTimersByTime(61_000);

    expect(getToken()).toBeNull();
  });

  it('clears the session and notifies on a 401', async () => {
    saveSession('stale', 3600);
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    mockFetch(401, { code: 'unauthorized', message: 'Invalid or expired token.' });

    await expect(request('/slots')).rejects.toBeInstanceOf(ApiError);

    expect(getToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('does not treat a failed login as a session expiry', async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    mockFetch(401, { code: 'unauthorized', message: 'Incorrect username or password.' });

    await expect(request('/auth/token', { method: 'POST', auth: false })).rejects.toThrow(
      'Incorrect username or password.',
    );
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
