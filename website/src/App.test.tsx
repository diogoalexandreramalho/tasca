import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { App } from '@/App';

vi.mock('@elevenlabs/react', () => ({
  ConversationProvider: ({ children }: { children: ReactNode }) => children,
  useConversation: () => ({ startSession: vi.fn(), endSession: vi.fn(), isSpeaking: false }),
}));

describe('App', () => {
  it('presents the restaurant, the call button, the photo and the opening hours', () => {
    render(<App />);

    expect(screen.getByText('Demo project · fictional restaurant')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Petiscos, vinho and a good conversation.' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Talk to Tasca' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Inside a traditional tasca/ })).toBeInTheDocument();

    const footer = screen.getByRole('contentinfo');
    expect(footer).toHaveTextContent('Tuesday to Sunday · closed on Mondays');
    expect(footer).toHaveTextContent('Lunch 12:00 · 13:30');
    expect(footer).toHaveTextContent('Dinner 19:00 · 20:30');
    expect(footer).toHaveTextContent('Parties of 1 to 8');
  });
});
