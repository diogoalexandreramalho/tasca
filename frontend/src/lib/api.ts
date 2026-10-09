const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

/** Error shape produced by the backend's AppException handler. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
};

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? 'GET',
    headers,
    body,
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.code ?? 'unknown',
      payload?.message ?? response.statusText,
      payload?.details,
    );
  }

  return payload as T;
}
