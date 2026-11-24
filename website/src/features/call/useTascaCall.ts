import { useConversation } from '@elevenlabs/react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError, createVoiceSession } from '@/lib/api';

/** ElevenLabs ends every call after this long (the agent's max duration). */
export const MAX_CALL_SECS = 180;
/** If the token takes longer than this, the API is probably waking up (Render Free). */
const SLOW_START_MS = 4000;

export type CallPhase =
  | 'idle'
  | 'starting' // asking for the microphone, then for a token
  | 'connecting' // token in hand, the SDK is connecting to ElevenLabs
  | 'live'
  | 'ended'
  | 'mic_blocked'
  | 'unavailable' // our API said no (not configured, daily limit, ElevenLabs down)
  | 'failed'; // couldn't reach the API, or the connection broke

/**
 * The whole "Talk to Tasca" call: microphone → token from our API → WebRTC
 * session with the private agent. Must be used inside `ConversationProvider`.
 */
export function useTascaCall() {
  const [phase, setPhase] = useState<CallPhase>('idle');
  const [slowStart, setSlowStart] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  const conversation = useConversation({
    onConnect: () => setPhase('live'),
    onDisconnect: (details) => {
      // A broken connection before the call started is a failure; anything
      // else (caller hung up, agent ended, 3-minute limit) is a normal end.
      setPhase(details.reason === 'error' && phaseRef.current !== 'live' ? 'failed' : 'ended');
    },
    onError: (message) => {
      console.error('Voice call error:', message);
      if (phaseRef.current !== 'live') setPhase('failed');
    },
  });

  const start = useCallback(async () => {
    setPhase('starting');
    setSlowStart(false);
    setElapsed(0);
    const slow = setTimeout(() => setSlowStart(true), SLOW_START_MS);
    try {
      // Ask first: the browser's permission prompt is the first thing people see,
      // and a blocked mic needs its own message.
      if (!(await microphoneAllowed())) {
        setPhase('mic_blocked');
        return;
      }
      const token = await createVoiceSession();
      setPhase('connecting');
      conversation.startSession({ conversationToken: token, connectionType: 'webrtc' });
    } catch (err) {
      setPhase(err instanceof ApiError ? 'unavailable' : 'failed');
    } finally {
      clearTimeout(slow);
    }
  }, [conversation]);

  const end = useCallback(() => conversation.endSession(), [conversation]);
  const reset = useCallback(() => setPhase('idle'), []);

  useEffect(() => {
    if (phase !== 'live') return;
    const startedAt = Date.now();
    const id = setInterval(() => {
      setElapsed(Math.min(MAX_CALL_SECS, Math.floor((Date.now() - startedAt) / 1000)));
    }, 1000);
    return () => clearInterval(id);
  }, [phase]);

  return {
    phase,
    slowStart,
    elapsed,
    isSpeaking: conversation.isSpeaking,
    start,
    end,
    reset,
  };
}

async function microphoneAllowed(): Promise<boolean> {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Only checking permission: the SDK opens its own stream.
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch {
    return false;
  }
}
