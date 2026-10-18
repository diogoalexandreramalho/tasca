import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { SlotAvailability } from '@/features/reservations/types';
import { clearSession, saveSession } from '@/lib/api';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

const FRIDAY = '2026-10-16';

function availability(reasons: (SlotAvailability['reason'])[]): SlotAvailability[] {
  return SLOTS.map((s, i) => ({
    service: s.service,
    start_time: s.start_time,
    end_time: s.end_time,
    available: reasons[i] === null,
    reason: reasons[i] ?? null,
  }));
}

beforeEach(() => saveSession('tok', 3600));
afterEach(() => {
  vi.unstubAllGlobals();
  clearSession();
});

async function openPanel() {
  fireEvent.click(await screen.findByRole('button', { name: '+ New booking' }));
  return screen.getByRole('dialog', { name: 'New booking' });
}

function fill(dialog: HTMLElement, label: string, value: string) {
  fireEvent.change(within(dialog).getByLabelText(label), { target: { value } });
}

describe('NewBookingPanel', () => {
  it('books the chosen sitting and shows it in the day view', async () => {
    let booked = false;
    const created = reservation({ slot: 4, table: 'M2', name: 'Ana Silva', date: FRIDAY });
    const fetchMock = mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, booked ? [created] : []),
      'GET /availability': () => json(200, availability([null, null, 'fully_booked', null])),
      'POST /reservations': () => {
        booked = true;
        return json(201, created);
      },
    });
    renderApp(`/?date=${FRIDAY}`);
    const dialog = await openPanel();

    // Defaults to the day being viewed and 2 guests; full sittings can't be picked.
    const full = await within(dialog).findByRole('radio', { name: /^19:00/ });
    expect(full).toBeDisabled();
    expect(within(dialog).getByText('Fully booked')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('radio', { name: /^20:30/ }));
    fill(dialog, 'Name', 'Ana Silva');
    fill(dialog, 'Phone', '912 345 678');
    fill(dialog, 'Notes', 'Alergia: marisco');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Book' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Booked Ana Silva · 2 guests · 20:30 at table M2.',
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(await screen.findByText('Ana Silva')).toBeInTheDocument();

    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      reservation_date: FRIDAY,
      start_time: '20:30',
      party_size: 2,
      customer_name: 'Ana Silva',
      phone: '912 345 678',
      notes: 'Alergia: marisco',
    });
    const availabilityUrl = fetchMock.mock.calls
      .map(([url]) => new URL(String(url)))
      .find((u) => u.pathname.endsWith('/availability'));
    expect(availabilityUrl?.searchParams.get('date')).toBe(FRIDAY);
    expect(availabilityUrl?.searchParams.get('party_size')).toBe('2');
  });

  it('rechecks availability when the party size changes', async () => {
    const fetchMock = mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /availability': (_, url) =>
        json(
          200,
          url.searchParams.get('party_size') === '8'
            ? availability(['fully_booked', 'fully_booked', null, 'fully_booked'])
            : availability([null, null, null, null]),
        ),
    });
    renderApp(`/?date=${FRIDAY}`);
    const dialog = await openPanel();
    await within(dialog).findByRole('radio', { name: /^12:00/ });

    fireEvent.change(within(dialog).getByLabelText('Guests'), { target: { value: '8' } });

    await waitFor(() =>
      expect(within(dialog).getByRole('radio', { name: /^12:00/ })).toBeDisabled(),
    );
    expect(within(dialog).getByRole('radio', { name: /^19:00/ })).toBeEnabled();
    const sizes = fetchMock.mock.calls
      .map(([url]) => new URL(String(url)))
      .filter((u) => u.pathname.endsWith('/availability'))
      .map((u) => u.searchParams.get('party_size'));
    expect(sizes).toEqual(['2', '8']);
  });

  it('explains a closed day once instead of per sitting', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /availability': () => json(200, availability(Array(4).fill('closed_day'))),
    });
    renderApp('/?date=2026-10-19');
    const dialog = await openPanel();

    expect(await within(dialog).findByText('Closed on Mondays')).toBeInTheDocument();
    expect(within(dialog).queryByRole('radio')).not.toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Book' })).toBeDisabled();
  });

  it('keeps the panel open and explains when the server rejects the booking', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /availability': () => json(200, availability([null, null, null, null])),
      'POST /reservations': () =>
        json(409, {
          code: 'booking_rejected',
          message: "The booking can't be made.",
          details: { reason: 'fully_booked' },
        }),
    });
    renderApp(`/?date=${FRIDAY}`);
    const dialog = await openPanel();

    fireEvent.click(await within(dialog).findByRole('radio', { name: /^12:00/ }));
    fill(dialog, 'Name', 'Rui');
    fill(dialog, 'Phone', '913 222 111');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Book' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      "Can't book: fully booked.",
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows validation messages from the server', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /availability': () => json(200, availability([null, null, null, null])),
      'POST /reservations': () =>
        json(422, { code: 'validation_error', message: 'Invalid phone number.', details: null }),
    });
    renderApp(`/?date=${FRIDAY}`);
    const dialog = await openPanel();

    fireEvent.click(await within(dialog).findByRole('radio', { name: /^12:00/ }));
    fill(dialog, 'Name', 'Rui');
    fill(dialog, 'Phone', '12345');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Book' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Invalid phone number.');
  });

  it('closes with Escape', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /availability': () => json(200, availability([null, null, null, null])),
    });
    renderApp(`/?date=${FRIDAY}`);
    await openPanel();

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
