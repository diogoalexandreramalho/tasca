import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { HomePage } from '@/features/home/HomePage';
import { json, mockApi } from '@/test/mockApi';

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HomePage />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('HomePage', () => {
  it('shows the API as online and lists the sittings', async () => {
    mockApi({
      'GET /health': () => json(200, { status: 'ok' }),
      'GET /slots': () =>
        json(200, [
          { id: 1, service: 'lunch', start_time: '12:00:00', end_time: '13:30:00' },
          { id: 2, service: 'dinner', start_time: '20:30:00', end_time: '22:00:00' },
        ]),
    });
    renderPage();
    expect(await screen.findByText('API online')).toBeInTheDocument();
    expect(await screen.findByText('Sittings: 12:00 · 20:30')).toBeInTheDocument();
  });

  it('shows the API as unreachable when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    renderPage();
    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
  });
});
