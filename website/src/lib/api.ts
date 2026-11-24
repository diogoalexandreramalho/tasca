const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

/** An error answer from our API (shape `{code, message, details}`). */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * A single-use token to talk to the agent, valid for a few minutes.
 * Throws ApiError if the API refuses (503 when the voice demo is unavailable),
 * or a TypeError if the API can't be reached at all.
 */
export async function createVoiceSession(): Promise<string> {
  const res = await fetch(`${API_URL}/voice/session`, { method: 'POST' });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { code?: string; message?: string } | null;
    throw new ApiError(res.status, body?.code ?? 'unknown', body?.message ?? res.statusText);
  }
  const { token } = (await res.json()) as { token: string };
  return token;
}
