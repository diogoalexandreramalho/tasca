import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { searchParamsFor } from '@/features/reservations/queries';
import { clearSession, saveSession } from '@/lib/api';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-10-14T09:00:00Z'));
  saveSession('tok', 3600);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  clearSession();
});

function searchFor(text: string) {
  const box = screen.getByRole('searchbox', { name: 'Search bookings by name or phone' });
  fireEvent.change(box, { target: { value: text } });
  fireEvent.submit(screen.getByRole('search'));
}

describe('searchParamsFor', () => {
  it('treats phone-looking input as a phone and anything else as a name', () => {
    expect(searchParamsFor('912 345 678')).toEqual({ phone: '912 345 678' });
    expect(searchParamsFor('+351912345678')).toEqual({ phone: '+351912345678' });
    expect(searchParamsFor('Ana')).toEqual({ name: 'Ana' });
    expect(searchParamsFor('M15')).toEqual({ name: 'M15' });
    expect(searchParamsFor('123')).toEqual({ name: '123' });
    expect(searchParamsFor('   ')).toBeNull();
  });
});

describe('SearchPage', () => {
  it('searches by name from the header and lists upcoming bookings across days', async () => {
    const fetchMock = mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': (_, url) =>
        url.searchParams.has('name')
          ? json(200, [
              reservation({ slot: 1, table: 'M1', name: 'Ana Silva', date: '2026-10-16' }),
              reservation({ slot: 4, table: 'M2', name: 'Ana Sousa', date: '2026-10-17' }),
            ])
          : json(200, []),
    });
    renderApp('/');
    await screen.findByText('Whole day: No bookings');

    searchFor('ana');

    expect(
      await screen.findByRole('heading', { name: 'Upcoming bookings for “ana”' }),
    ).toBeInTheDocument();
    const results = await screen.findByRole('region', { name: 'Search results' });
    expect(within(results).getByText('2 bookings')).toBeInTheDocument();
    expect(within(results).getByText('Ana Silva')).toBeInTheDocument();
    expect(within(results).getByRole('link', { name: /Sat 17 Oct/ })).toHaveAttribute(
      'href',
      '/?date=2026-10-17',
    );

    const searchUrl = fetchMock.mock.calls
      .map(([url]) => new URL(String(url)))
      .find((u) => u.searchParams.has('name'));
    expect(searchUrl?.searchParams.get('name')).toBe('ana');
  });

  it('searches by phone when the query looks like a number', async () => {
    const fetchMock = mockApi({
      'GET /reservations': () => json(200, [reservation({ name: 'Ana Silva' })]),
    });
    renderApp('/search?q=912%20345%20678');

    expect(await screen.findByText('Ana Silva')).toBeInTheDocument();
    expect(screen.getByText('Matching this phone number.')).toBeInTheDocument();
    const url = new URL(String(fetchMock.mock.calls[0]![0]));
    expect(url.searchParams.get('phone')).toBe('912 345 678');
    expect(url.searchParams.has('name')).toBe(false);
  });

  it('says so when nothing matches', async () => {
    mockApi({ 'GET /reservations': () => json(200, []) });
    renderApp('/search?q=Zeferino');

    expect(await screen.findByText('No upcoming bookings found.')).toBeInTheDocument();
  });

  it('shows the server message for an invalid phone number', async () => {
    mockApi({
      'GET /reservations': () =>
        json(422, { code: 'validation_error', message: 'Invalid phone number.' }),
    });
    renderApp('/search?q=000000');

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid phone number.');
  });

  it('lets you cancel from the results', async () => {
    const ana = reservation({ name: 'Ana Silva' });
    mockApi({
      'GET /reservations': () => json(200, [ana]),
      [`POST /reservations/${ana.id}/cancel`]: () => json(200, { ...ana, status: 'cancelled' }),
    });
    renderApp('/search?q=ana');

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking for Ana Silva' }));
    fireEvent.click(screen.getByRole('button', { name: 'Yes, cancel' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Cancelled Ana Silva');
  });
});
