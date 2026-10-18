import { vi } from 'vitest';

type Handler = (init: RequestInit | undefined, url: URL) => Response | Promise<Response>;

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status });
}

/**
 * Stub `fetch` with handlers keyed by "METHOD /path" (path relative to /api/v1,
 * query string not part of the key; handlers get the full URL). Unknown routes
 * fail the test loudly.
 */
export function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const path = url.pathname.replace(/^\/api\/v1/, '');
    const key = `${init?.method ?? 'GET'} ${path}`;
    const handler = routes[key];
    if (!handler) throw new Error(`Unmocked request: ${key}`);
    return handler(init, url);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
