import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from '@/app/App';
import { AuthProvider } from '@/features/auth/AuthContext';
import { clearSession, getToken, saveSession } from '@/lib/api';
import { json, mockApi } from '@/test/mockApi';

const SLOTS = [{ id: 1, service: 'lunch', start_time: '12:00:00', end_time: '13:30:00' }];

function renderApp(route = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[route]}>
          <App />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

async function submitLogin(password: string) {
  fireEvent.change(await screen.findByLabelText('Password'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  clearSession();
});

describe('login flow', () => {
  it('sends visitors without a session to the login page', async () => {
    mockApi({});
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Log out' })).not.toBeInTheDocument();
  });

  it('logs in, stores the token and shows the dashboard', async () => {
    const fetchMock = mockApi({
      'POST /auth/token': () =>
        json(200, { access_token: 'tok-123', token_type: 'bearer', expires_in: 43200 }),
      'GET /health': () => json(200, { status: 'ok' }),
      'GET /slots': () => json(200, SLOTS),
    });
    renderApp('/');

    await submitLogin('right-password');

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    expect(await screen.findByText('Sittings: 12:00')).toBeInTheDocument();
    expect(getToken()).toBe('tok-123');
    const slotsCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/slots'));
    expect((slotsCall?.[1]?.headers as Record<string, string>)['Authorization']).toBe(
      'Bearer tok-123',
    );
  });

  it('shows the server message on wrong credentials', async () => {
    mockApi({
      'POST /auth/token': () =>
        json(401, { code: 'unauthorized', message: 'Incorrect username or password.' }),
    });
    renderApp('/');

    await submitLogin('wrong-password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect username or password.');
    expect(getToken()).toBeNull();
  });

  it('logs out back to the login page', async () => {
    saveSession('tok-123', 3600);
    mockApi({
      'GET /health': () => json(200, { status: 'ok' }),
      'GET /slots': () => json(200, SLOTS),
    });
    renderApp('/');

    fireEvent.click(await screen.findByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it('returns to the login page when the API rejects the token', async () => {
    saveSession('revoked', 3600);
    mockApi({
      'GET /health': () => json(200, { status: 'ok' }),
      'GET /slots': () => json(401, { code: 'unauthorized', message: 'Invalid or expired token.' }),
    });
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});
