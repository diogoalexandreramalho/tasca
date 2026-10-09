import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, request } from '@/lib/api';

function mockFetch(status: number, payload: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(payload === undefined ? null : JSON.stringify(payload), { status }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
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

  it('maps backend errors to ApiError', async () => {
    mockFetch(404, { code: 'not_found', message: 'Reservation not found.', details: null });

    const error = await request('/reservations/X').catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, code: 'not_found', message: 'Reservation not found.' });
  });

  it('returns undefined for 204 No Content', async () => {
    mockFetch(204, undefined);
    await expect(request('/things/1', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});
