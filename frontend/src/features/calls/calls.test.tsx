import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Call, CallDetail } from '@/features/calls/types';
import { clearSession, saveSession } from '@/lib/api';
import { SLOTS, reservation } from '@/test/fixtures';
import { json, mockApi } from '@/test/mockApi';
import { renderApp } from '@/test/renderApp';

const BOOKED: Call = {
  id: 'call-1',
  conversation_id: 'conv_booked',
  started_at: '2026-11-06T19:02:00Z', // 19:02 in Lisbon (winter time)
  duration_secs: 134,
  outcome: 'booked',
  summary: 'Caller booked dinner for four.',
  bookings: [
    {
      id: 'res-1',
      action: 'created',
      reservation_date: '2026-11-13',
      start_time: '20:30:00',
      party_size: 4,
      customer_name: 'Ana',
      status: 'confirmed',
    },
  ],
};
const ENQUIRY: Call = {
  id: 'call-2',
  conversation_id: 'conv_enquiry',
  started_at: '2026-11-06T18:10:00Z',
  duration_secs: 41,
  outcome: 'enquiry',
  summary: 'Asked about Monday; we are closed.',
  bookings: [],
};
const BOOKED_DETAIL: CallDetail = {
  ...BOOKED,
  transcript: [
    { role: 'agent', message: 'Hello, how can I help?', time_in_call_secs: 0 },
    { role: 'user', message: 'A table for four next Friday.', time_in_call_secs: 4 },
  ],
};

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-11-06T20:00:00Z'));
  saveSession('tok', 3600);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  clearSession();
});

describe('CallsPage', () => {
  it('lists the day’s calls with time, duration, outcome, summary and bookings', async () => {
    const fetchMock = mockApi({ 'GET /calls': () => json(200, [BOOKED, ENQUIRY]) });
    renderApp('/calls?date=2026-11-06');

    const list = await screen.findByRole('region', { name: 'Calls' });
    expect(within(list).getByText('2 calls')).toBeInTheDocument();
    const first = within(list).getByRole('button', { name: 'Open the call at 19:02' });
    expect(first).toHaveTextContent('2:14');
    expect(first).toHaveTextContent('Booked');
    expect(first).toHaveTextContent('Caller booked dinner for four.');
    expect(within(list).getByRole('link', { name: /Booked Fri 13 Nov 20:30/ })).toHaveAttribute(
      'href',
      '/?date=2026-11-13',
    );
    expect(within(list).getByRole('button', { name: 'Open the call at 18:10' })).toHaveTextContent(
      'Enquiry',
    );
    const url = new URL(String(fetchMock.mock.calls[0]![0]));
    expect(url.searchParams.get('date')).toBe('2026-11-06');
  });

  it('says so when there are no calls', async () => {
    mockApi({ 'GET /calls': () => json(200, []) });
    renderApp('/calls?date=2026-11-06');

    expect(await screen.findByText('No calls on this day.')).toBeInTheDocument();
  });

  it('opens a call in the side panel with its conversation', async () => {
    mockApi({
      'GET /calls': () => json(200, [BOOKED]),
      'GET /calls/by-conversation/conv_booked': () => json(200, BOOKED_DETAIL),
    });
    renderApp('/calls?date=2026-11-06');

    fireEvent.click(await screen.findByRole('button', { name: 'Open the call at 19:02' }));

    const panel = await screen.findByRole('dialog', { name: 'Call' });
    const conversation = await within(panel).findByRole('region', { name: 'Conversation' });
    expect(within(conversation).getByText('Hello, how can I help?')).toBeInTheDocument();
    expect(within(conversation).getByText('Caller · 0:04')).toBeInTheDocument();
    expect(within(panel).getByText('Caller booked dinner for four.')).toBeInTheDocument();
    expect(within(panel).getByRole('link', { name: 'Open day' })).toHaveAttribute(
      'href',
      '/?date=2026-11-13',
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows that old summaries and conversations were removed', async () => {
    mockApi({
      'GET /calls': () => json(200, []),
      'GET /calls/by-conversation/conv_old': () =>
        json(200, { ...BOOKED_DETAIL, conversation_id: 'conv_old', summary: null, transcript: null }),
    });
    renderApp('/calls?date=2026-11-06&call=conv_old');

    expect(
      await screen.findByText('Summary and conversation removed after 90 days.'),
    ).toBeInTheDocument();
  });

  it('explains a call that was never recorded', async () => {
    mockApi({
      'GET /calls': () => json(200, []),
      'GET /calls/by-conversation/conv_missing': () =>
        json(404, { code: 'not_found', message: 'Call not found.' }),
    });
    renderApp('/calls?call=conv_missing');

    expect(await screen.findByRole('alert')).toHaveTextContent('This call hasn’t been recorded');
  });
});

describe('booking → call link', () => {
  it('phone bookings open their call over the day view', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () =>
        json(200, [
          reservation({ slot: 4, table: 'M1', name: 'Ana', conversationId: 'conv_booked', date: '2026-11-13' }),
          reservation({ slot: 4, table: 'M2', name: 'Rui', date: '2026-11-13' }),
        ]),
      'GET /calls/by-conversation/conv_booked': () => json(200, BOOKED_DETAIL),
    });
    renderApp('/?date=2026-11-13');

    // Only the booking made by the agent has the link.
    fireEvent.click(await screen.findByRole('button', { name: 'View the call that booked Ana' }));
    expect(
      screen.queryByRole('button', { name: 'View the call that booked Rui' }),
    ).not.toBeInTheDocument();

    const panel = await screen.findByRole('dialog', { name: 'Call' });
    expect(await within(panel).findByText('Hello, how can I help?')).toBeInTheDocument();
    // Still on the day view underneath.
    expect(screen.getByRole('heading', { name: 'Friday, 13 November 2026' })).toBeInTheDocument();
  });
});

describe('navigation', () => {
  it('links to Bookings and Calls', async () => {
    mockApi({
      'GET /slots': () => json(200, SLOTS),
      'GET /reservations': () => json(200, []),
      'GET /calls': () => json(200, []),
    });
    renderApp('/');

    const nav = await screen.findByRole('navigation', { name: 'Main' });
    fireEvent.click(within(nav).getByRole('link', { name: 'Calls' }));

    expect(await screen.findByText('No calls on this day.')).toBeInTheDocument();
  });
});
