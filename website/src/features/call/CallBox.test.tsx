import { act, fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CallBox } from '@/features/call/CallBox';

// Fake ElevenLabs SDK: records the callbacks our hook registers and the session
// it starts, so tests can play the conversation's events.
type Callbacks = {
  onConnect?: () => void;
  onDisconnect?: (details: { reason: string }) => void;
  onError?: (message: string) => void;
};
const sdk = vi.hoisted(() => ({
  callbacks: {} as Callbacks,
  startSession: vi.fn(),
  endSession: vi.fn(),
  isSpeaking: false,
}));
vi.mock('@elevenlabs/react', () => ({
  ConversationProvider: ({ children }: { children: ReactNode }) => children,
  useConversation: (callbacks: Callbacks) => {
    sdk.callbacks = callbacks;
    return {
      startSession: sdk.startSession,
      endSession: sdk.endSession,
      isSpeaking: sdk.isSpeaking,
    };
  },
}));

const getUserMedia = vi.fn();
const fetchMock = vi.fn();

function micAllowed() {
  getUserMedia.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
}
function tokenReply() {
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ token: 'tok_123' }), { status: 200 }));
}

beforeEach(() => {
  sdk.callbacks = {};
  sdk.isSpeaking = false;
  sdk.startSession.mockReset();
  sdk.endSession.mockReset();
  getUserMedia.mockReset();
  fetchMock.mockReset();
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function clickTalk() {
  fireEvent.click(screen.getByRole('button', { name: 'Talk to Tasca' }));
  // Let the mic check and the token request settle.
  await act(async () => {});
}

describe('CallBox', () => {
  it('shows the button with an example request', () => {
    render(<CallBox />);

    expect(screen.getByRole('button', { name: 'Talk to Tasca' })).toBeInTheDocument();
    expect(screen.getByText(/book a table for tomorrow at 8pm/)).toBeInTheDocument();
  });

  it('gets a token from our API and starts a private WebRTC session with it', async () => {
    micAllowed();
    tokenReply();
    render(<CallBox />);

    await clickTalk();

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toMatch(/\/voice\/session$/);
    expect(init).toMatchObject({ method: 'POST' });
    expect(sdk.startSession).toHaveBeenCalledWith({
      conversationToken: 'tok_123',
      connectionType: 'webrtc',
    });
    expect(screen.getByText('Connecting…')).toBeInTheDocument();
  });

  it('shows who is talking and a timer during the call, and ends it on request', async () => {
    micAllowed();
    tokenReply();
    render(<CallBox />);
    await clickTalk();

    act(() => sdk.callbacks.onConnect?.());

    expect(screen.getByText('Listening')).toBeInTheDocument();
    expect(screen.getByText('0:00 / 3:00')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'End call' }));
    expect(sdk.endSession).toHaveBeenCalled();

    act(() => sdk.callbacks.onDisconnect?.({ reason: 'user' }));
    expect(screen.getByText('Obrigado! See you soon.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Talk again' }));
    expect(screen.getByRole('button', { name: 'Talk to Tasca' })).toBeInTheDocument();
  });

  it('says when the agent is speaking', async () => {
    micAllowed();
    tokenReply();
    sdk.isSpeaking = true;
    render(<CallBox />);
    await clickTalk();

    act(() => sdk.callbacks.onConnect?.());

    expect(screen.getByText('Tasca is speaking')).toBeInTheDocument();
  });

  it('explains a blocked microphone without asking for a token', async () => {
    getUserMedia.mockRejectedValue(new DOMException('denied', 'NotAllowedError'));
    render(<CallBox />);

    await clickTalk();

    expect(screen.getByText('Your microphone is blocked')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(sdk.startSession).not.toHaveBeenCalled();
  });

  it('says calls are unavailable when the API refuses (daily limit, not configured)', async () => {
    micAllowed();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: 'service_unavailable', message: 'x', details: null }), {
        status: 503,
      }),
    );
    render(<CallBox />);

    await clickTalk();

    expect(screen.getByText('We can’t take calls right now')).toBeInTheDocument();
    expect(sdk.startSession).not.toHaveBeenCalled();
  });

  it('says the call failed when the API is unreachable', async () => {
    micAllowed();
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    render(<CallBox />);

    await clickTalk();

    expect(screen.getByText('The call couldn’t connect')).toBeInTheDocument();
  });

  it('says the call failed when the connection breaks before it starts', async () => {
    micAllowed();
    tokenReply();
    render(<CallBox />);
    await clickTalk();

    act(() => sdk.callbacks.onDisconnect?.({ reason: 'error' }));

    expect(screen.getByText('The call couldn’t connect')).toBeInTheDocument();
  });

  it('mentions waking up when the API is slow to answer', async () => {
    vi.useFakeTimers();
    micAllowed();
    fetchMock.mockReturnValue(new Promise(() => {})); // never answers
    render(<CallBox />);

    fireEvent.click(screen.getByRole('button', { name: 'Talk to Tasca' }));
    expect(screen.getByText('Connecting…')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(screen.getByText('Waking up the restaurant…')).toBeInTheDocument();
  });
});
