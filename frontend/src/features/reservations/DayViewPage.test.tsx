import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { clearSession, saveSession } from '@/lib/api';
import { todayInLisbon } from '@/lib/dates';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

const FRIDAY = [
  reservation({ slot: 1, table: 'M1', name: 'Ana Silva', notes: 'Alergia: marisco' }),
  reservation({ slot: 1, table: 'M7', name: 'Rui Costa', party_size: 4, phone: '+351913222111' }),
  reservation({ slot: 3, table: 'M15', name: 'Festa Sousa', party_size: 6, notes: 'Aniversário' }),
];

function mockDay(reservations = FRIDAY) {
  return mockApi({
    'GET /slots': () => json(200, SLOTS),
    'GET /reservations': () => json(200, reservations),
  });
}

function requestedDates(fetchMock: ReturnType<typeof mockApi>): string[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((u) => u.pathname.endsWith('/reservations'))
    .map((u) => u.searchParams.get('date')!);
}

beforeEach(() => saveSession('tok', 3600));
afterEach(() => {
  vi.unstubAllGlobals();
  clearSession();
});

describe('DayViewPage', () => {
  it('shows every sitting, with bookings grouped under it', async () => {
    mockDay();
    renderApp('/?date=2026-10-16');

    expect(screen.getByRole('heading', { name: 'Friday, 16 October 2026' })).toBeInTheDocument();

    const lunch = await screen.findByRole('region', { name: '12:00–13:30 · Lunch' });
    expect(within(lunch).getByText('2 bookings · 6 guests')).toBeInTheDocument();
    expect(within(lunch).getByText('Ana Silva')).toBeInTheDocument();
    expect(within(lunch).getByText('Rui Costa')).toBeInTheDocument();
    expect(within(lunch).getByText('913 222 111')).toBeInTheDocument();

    const lateLunch = screen.getByRole('region', { name: '13:30–15:00 · Lunch' });
    expect(within(lateLunch).getByText('No bookings')).toBeInTheDocument();

    const dinner = screen.getByRole('region', { name: '19:00–20:30 · Dinner' });
    expect(within(dinner).getByText('Festa Sousa')).toBeInTheDocument();
    expect(within(dinner).getByText('1 booking · 6 guests')).toBeInTheDocument();

    expect(screen.getByText('Whole day: 3 bookings · 12 guests')).toBeInTheDocument();
  });

  it('highlights allergy notes but not other notes', async () => {
    mockDay();
    renderApp('/?date=2026-10-16');

    const allergy = await screen.findByText('Alergia: marisco');
    expect(allergy.closest('[data-allergy]')).not.toBeNull();
    expect(screen.getByText('Aniversário').closest('[data-allergy]')).toBeNull();
  });

  it('defaults to today in Lisbon', async () => {
    const fetchMock = mockDay([]);
    renderApp('/');

    await screen.findByText('Whole day: No bookings');
    expect(requestedDates(fetchMock)).toEqual([todayInLisbon()]);
  });

  it('moves between days with the arrows', async () => {
    const fetchMock = mockDay([]);
    renderApp('/?date=2026-10-16');
    await screen.findByText('Whole day: No bookings');

    fireEvent.click(screen.getByRole('button', { name: 'Next day' }));
    expect(
      await screen.findByRole('heading', { name: 'Saturday, 17 October 2026' }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Previous day' }));
    fireEvent.click(screen.getByRole('button', { name: 'Previous day' }));
    expect(
      await screen.findByRole('heading', { name: 'Thursday, 15 October 2026' }),
    ).toBeInTheDocument();

    // Passing back through Friday refetches it, so staff always see fresh bookings.
    expect(requestedDates(fetchMock)).toEqual([
      '2026-10-16',
      '2026-10-17',
      '2026-10-16',
      '2026-10-15',
    ]);
  });

  it('shows an error when bookings fail to load', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(500, { code: 'internal_error', message: 'Boom.' }),
    });
    renderApp('/?date=2026-10-16');

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load bookings: Boom.');
  });
});
