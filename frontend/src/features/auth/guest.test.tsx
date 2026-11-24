import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { clearSession, getSessionRole, getToken, saveSession } from '@/lib/api';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

// What the API sends a guest: phone numbers already masked.
const MASKED = reservation({ slot: 4, table: 'M2', name: 'Ana Silva', phone: '+351•••••••78' });
const DAY_VIEW = {
  'GET /slots': () => json(200, SLOTS),
  'GET /reservations': () => json(200, [MASKED]),
};

beforeEach(() => {
  // Wednesday 14 Oct 2026: the Friday booking hasn't started, so admins could cancel it.
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-10-14T09:00:00Z'));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  clearSession();
});

describe('guest demo', () => {
  it('enters without a password from the login page', async () => {
    const fetchMock = mockApi({
      'POST /auth/guest': () =>
        json(200, { access_token: 'guest-tok', token_type: 'bearer', expires_in: 43200 }),
      ...DAY_VIEW,
    });
    renderApp('/?date=2026-10-16');

    fireEvent.click(await screen.findByRole('button', { name: 'Explore as a guest' }));

    expect(await screen.findByText('Guest · read-only')).toBeInTheDocument();
    expect(getToken()).toBe('guest-tok');
    expect(getSessionRole()).toBe('guest');
    const login = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/guest'));
    expect(login?.[1]?.body).toBeUndefined(); // no credentials sent
  });

  it('shows bookings with masked phones but no way to change them', async () => {
    saveSession('guest-tok', 3600, 'guest');
    mockApi(DAY_VIEW);
    renderApp('/?date=2026-10-16');

    const row = (await screen.findByText('Ana Silva')).closest('li')!;
    expect(within(row).getByText('••• ••• •78')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '+ New booking' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Cancel booking for Ana Silva' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Leave demo' })).toBeInTheDocument();
  });

  it('keeps the actions for the admin (control for the test above)', async () => {
    saveSession('admin-tok', 3600);
    mockApi(DAY_VIEW);
    renderApp('/?date=2026-10-16');

    expect(
      await screen.findByRole('button', { name: 'Cancel booking for Ana Silva' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '+ New booking' })).toBeInTheDocument();
    expect(screen.queryByText('Guest · read-only')).not.toBeInTheDocument();
  });

  it('searches by name only', async () => {
    saveSession('guest-tok', 3600, 'guest');
    const fetchMock = mockApi(DAY_VIEW);
    renderApp('/search?q=912%20345%20678');

    expect(
      await screen.findByText(/Searching by phone isn’t available in the demo/),
    ).toBeInTheDocument();
    expect(screen.getByRole('searchbox', { name: 'Search bookings by name' })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('phone='))).toBe(false);
  });

  it('explains when guest access is turned off', async () => {
    mockApi({
      'POST /auth/guest': () =>
        json(403, { code: 'forbidden', message: 'Guest access is turned off.', details: null }),
    });
    renderApp('/');

    fireEvent.click(await screen.findByRole('button', { name: 'Explore as a guest' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Guest access is turned off.');
    expect(getToken()).toBeNull();
  });
});
