const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
const SESSION_KEY = 'tasca.session';

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

type Session = { token: string; expiresAt: number };

/** The stored bearer token, or null if there is none or it has expired. */
export function getToken(): string | null {
  const session = readSession();
  if (!session) return null;
  if (Date.now() >= session.expiresAt) {
    clearSession();
    return null;
  }
  return session.token;
}

export function getSessionExpiry(): number | null {
  return readSession()?.expiresAt ?? null;
}

export function saveSession(token: string, expiresInSeconds: number): void {
  const session: Session = { token, expiresAt: Date.now() + expiresInSeconds * 1000 };
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Storage unavailable (private mode): the user just has to log in again on reload.
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    // Nothing stored, nothing to clear.
  }
}

function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

let onUnauthorized: (() => void) | null = null;

/** Called when an authenticated request gets a 401 (token expired or revoked). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  /** Sent as application/x-www-form-urlencoded (OAuth2 login). */
  form?: URLSearchParams;
  /** Attach the bearer token. Default true. */
  auth?: boolean;
};

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (opts.form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const useAuth = opts.auth !== false;
  if (useAuth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? 'GET',
    headers,
    body,
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && useAuth) {
      clearSession();
      onUnauthorized?.();
    }
    throw new ApiError(
      response.status,
      payload?.code ?? 'unknown',
      payload?.message ?? response.statusText,
      payload?.details,
    );
  }

  return payload as T;
}
