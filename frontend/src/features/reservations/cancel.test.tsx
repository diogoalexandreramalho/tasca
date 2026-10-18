import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { clearSession, saveSession } from '@/lib/api';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

const ana = reservation({ slot: 1, table: 'M1', name: 'Ana Silva' });
const rui = reservation({ slot: 3, table: 'M7', name: 'Rui Costa', party_size: 4 });

beforeEach(() => {
  // Wednesday 14 Oct, 10:00 Lisbon: Friday's sittings haven't started.
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-10-14T09:00:00Z'));
  saveSession('tok', 3600);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  clearSession();
});

function mockDayWithCancel(cancel: () => Response) {
  let cancelled = false;
  const fetchMock = mockApi({
    'GET /slots': () => json(200, SLOTS),
    'GET /reservations': () => json(200, cancelled ? [rui] : [ana, rui]),
    [`POST /reservations/${ana.id}/cancel`]: () => {
      const response = cancel();
      cancelled = response.ok;
      return response;
    },
  });
  return fetchMock;
}

describe('cancelling from the day view', () => {
  it('asks for confirmation, cancels and frees the table', async () => {
    const fetchMock = mockDayWithCancel(() => json(200, { ...ana, status: 'cancelled' }));
    renderApp('/?date=2026-10-16');

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking for Ana Silva' }));
    const confirm = screen.getByRole('group', { name: 'Confirm cancellation' });
    expect(confirm).toHaveTextContent("Cancel Ana Silva's booking (Fri 16 Oct, 12:00, M1)?");

    fireEvent.click(within(confirm).getByRole('button', { name: 'Yes, cancel' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Cancelled Ana Silva · 2 guests · 12:00 at table M1. The table is free again.',
    );
    await waitFor(() => expect(screen.queryByText('Ana Silva')).not.toBeInTheDocument());
    expect(screen.getByText('Rui Costa')).toBeInTheDocument();
    const cancelCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/cancel'));
    expect(cancelCalls).toHaveLength(1);
  });

  it('"Keep" closes the confirmation without cancelling', async () => {
    const fetchMock = mockDayWithCancel(() => json(200, {}));
    renderApp('/?date=2026-10-16');

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking for Ana Silva' }));
    fireEvent.click(screen.getByRole('button', { name: 'Keep' }));

    expect(screen.queryByRole('group', { name: 'Confirm cancellation' })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/cancel'))).toBe(false);
  });

  it('shows the server message if the cancellation is refused', async () => {
    mockDayWithCancel(() =>
      json(409, { code: 'conflict', message: 'Reservation has already started.' }),
    );
    renderApp('/?date=2026-10-16');

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking for Ana Silva' }));
    fireEvent.click(screen.getByRole('button', { name: 'Yes, cancel' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Reservation has already started.');
    expect(screen.getByText('Ana Silva')).toBeInTheDocument();
  });

  it('offers no cancel button once a sitting has started', async () => {
    vi.setSystemTime(new Date('2026-10-16T11:15:00Z')); // Friday 12:15 Lisbon
    saveSession('tok', 3600); // the one from beforeEach expired when the clock moved
    mockDayWithCancel(() => json(200, {}));
    renderApp('/?date=2026-10-16');

    await screen.findByText('Ana Silva');
    expect(
      screen.queryByRole('button', { name: 'Cancel booking for Ana Silva' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel booking for Rui Costa' })).toBeInTheDocument();
  });
});
