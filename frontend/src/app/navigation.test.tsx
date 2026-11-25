import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearSession, saveSession } from '@/lib/api';
import { SLOTS } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

afterEach(() => {
  vi.unstubAllGlobals();
  clearSession();
});

describe('navigation', () => {
  it('keeps the search text in the box on the search page', async () => {
    saveSession('tok', 3600);
    mockApi({ 'GET /reservations': () => json(200, []) });
    renderApp('/search?q=Ana');

    expect(await screen.findByRole('searchbox')).toHaveValue('Ana');
  });

  it('returns to the same day after logging in', async () => {
    const fetchMock = mockApi({
      'POST /auth/token': () =>
        json(200, { access_token: 'tok', token_type: 'bearer', expires_in: 3600 }),
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
    });
    renderApp('/?date=2026-11-27');

    fireEvent.change(await screen.findByLabelText('Password'), { target: { value: 'pw' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByRole('heading', { name: 'Friday, 27 November 2026' }),
    ).toBeInTheDocument();
    const day = fetchMock.mock.calls.find(([url]) => String(url).includes('/reservations?'));
    expect(new URL(String(day?.[0])).searchParams.get('date')).toBe('2026-11-27');
  });
});
