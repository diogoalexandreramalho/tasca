import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router';

import { useAuth } from '@/features/auth/AuthContext';
import { ApiError } from '@/lib/api';

export function LoginPage() {
  const { isAuthenticated, login, loginAsGuest } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isEnteringAsGuest, setIsEnteringAsGuest] = useState(false);

  if (isAuthenticated) return <Navigate to={from} replace />;

  async function handleGuest() {
    setError(null);
    setIsEnteringAsGuest(true);
    try {
      await loginAsGuest();
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.');
    } finally {
      setIsEnteringAsGuest(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto mt-12 max-w-sm rounded-lg border border-stone-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <p className="mt-1 text-sm text-stone-600">Staff access to reservations.</p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Username
          <input
            className="rounded-md border border-stone-300 px-3 py-2 font-normal"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Password
          <input
            className="rounded-md border border-stone-300 px-3 py-2 font-normal"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            autoFocus
            required
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-stone-400" aria-hidden>
        <span className="h-px flex-1 bg-stone-200" />
        or
        <span className="h-px flex-1 bg-stone-200" />
      </div>
      <button
        type="button"
        onClick={handleGuest}
        disabled={isEnteringAsGuest}
        className="w-full rounded-md border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100 disabled:opacity-50"
      >
        {isEnteringAsGuest ? 'Opening the demo…' : 'Explore as a guest'}
      </button>
      <p className="mt-2 text-center text-xs text-stone-500">
        Read-only demo: browse bookings and calls. Phone numbers are hidden.
      </p>
    </section>
  );
}
