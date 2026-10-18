import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearSession, getToken, saveSession } from '@/lib/api';
import { SLOTS } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

const DAY_VIEW = {
  'GET /slots': () => json(200, SLOTS),
  'GET /reservations': () => json(200, []),
};

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

  it('logs in, stores the token and shows the day view', async () => {
    const fetchMock = mockApi({
      'POST /auth/token': () =>
        json(200, { access_token: 'tok-123', token_type: 'bearer', expires_in: 43200 }),
      ...DAY_VIEW,
    });
    renderApp('/');

    await submitLogin('right-password');

    expect(await screen.findByText('Whole day: No bookings')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '12:00–13:30 · Lunch' })).toBeInTheDocument();
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
    mockApi(DAY_VIEW);
    renderApp('/');

    fireEvent.click(await screen.findByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it('returns to the login page when the API rejects the token', async () => {
    saveSession('revoked', 3600);
    mockApi({
      'GET /slots': () => json(401, { code: 'unauthorized', message: 'Invalid or expired token.' }),
      'GET /reservations': () =>
        json(401, { code: 'unauthorized', message: 'Invalid or expired token.' }),
    });
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});
