import type { ReactNode } from 'react';

import { TalkButton } from '@/features/call/TalkButton';
import { MAX_CALL_SECS, useTascaCall } from '@/features/call/useTascaCall';

/** The "Talk to Tasca" button, and everything the call shows in its place. */
export function CallBox() {
  const call = useTascaCall();

  return (
    <div aria-live="polite" className="flex min-h-32 flex-col items-start justify-center gap-3">
      {call.phase === 'idle' && <TalkButton onClick={call.start} />}

      {call.phase === 'starting' &&
        (call.slowStart ? (
          <Status icon={<PhoneIcon />} title="Waking up the restaurant…">
            The first call in a while can take up to a minute.
          </Status>
        ) : (
          <Status icon={<PhoneIcon />} title="Connecting…">
            Allow the microphone if your browser asks.
          </Status>
        ))}

      {call.phase === 'connecting' && <Status icon={<PhoneIcon />} title="Connecting…" />}

      {call.phase === 'live' && (
        <>
          <div className="flex items-center gap-4">
            <VoiceBars active={call.isSpeaking} />
            <div>
              <p className="text-base">{call.isSpeaking ? 'Tasca is speaking' : 'Listening'}</p>
              <p className="text-sm text-azulejo-600 tabular-nums">
                {clock(call.elapsed)} / {clock(MAX_CALL_SECS)}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={call.end}
            className="rounded-full bg-terracotta-400 px-5 py-2 text-sm font-medium text-white hover:bg-terracotta-600"
          >
            End call
          </button>
        </>
      )}

      {call.phase === 'ended' && (
        <>
          <Status icon={<CheckIcon />} tone="done" title="Obrigado! See you soon." />
          <SecondaryButton onClick={call.reset}>Talk again</SecondaryButton>
        </>
      )}

      {call.phase === 'mic_blocked' && (
        <>
          <Status icon={<MicOffIcon />} tone="problem" title="Your microphone is blocked">
            Allow it from the icon in your browser’s address bar, then try again.
          </Status>
          <SecondaryButton onClick={call.reset}>Try again</SecondaryButton>
        </>
      )}

      {call.phase === 'unavailable' && (
        <>
          <Status icon={<MoonIcon />} tone="quiet" title="We can’t take calls right now">
            The demo has a daily limit. Try again tomorrow.
          </Status>
          <SecondaryButton onClick={call.reset}>Back</SecondaryButton>
        </>
      )}

      {call.phase === 'failed' && (
        <>
          <Status icon={<PhoneIcon />} tone="problem" title="The call couldn’t connect">
            Check your connection and try again.
          </Status>
          <SecondaryButton onClick={call.reset}>Try again</SecondaryButton>
        </>
      )}
    </div>
  );
}

const TONES = {
  normal: { circle: 'bg-azulejo-400', title: 'text-azulejo-800', body: 'text-azulejo-600' },
  done: { circle: 'bg-emerald-600', title: 'text-azulejo-800', body: 'text-azulejo-600' },
  problem: {
    circle: 'bg-terracotta-400',
    title: 'text-terracotta-800',
    body: 'text-terracotta-600',
  },
  quiet: { circle: 'bg-stone-400', title: 'text-azulejo-800', body: 'text-azulejo-600' },
};

function Status({
  icon,
  title,
  tone = 'normal',
  children,
}: {
  icon: ReactNode;
  title: string;
  tone?: keyof typeof TONES;
  children?: ReactNode;
}) {
  const t = TONES[tone];
  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex size-11 shrink-0 items-center justify-center rounded-full text-white ${t.circle}`}
      >
        {icon}
      </span>
      <div>
        <p className={`text-base ${t.title}`}>{title}</p>
        {children && <p className={`text-sm ${t.body}`}>{children}</p>}
      </div>
    </div>
  );
}

function SecondaryButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-azulejo-600 px-5 py-2 text-sm text-azulejo-800 hover:bg-azulejo-50"
    >
      {children}
    </button>
  );
}

function VoiceBars({ active }: { active: boolean }) {
  return (
    <span aria-hidden className="flex h-6 items-center gap-1">
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1 rounded-full bg-azulejo-600"
          style={
            active
              ? { animation: 'voice-bar 0.9s ease-in-out infinite', animationDelay: `${i * 0.12}s` }
              : undefined
          }
        />
      ))}
    </span>
  );
}

function clock(secs: number): string {
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
}

// Small inline icons (no icon library for five glyphs).
const iconProps = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

function MicOffIcon() {
  return (
    <svg {...iconProps}>
      <path d="M3 3l18 18M9 5a3 3 0 0 1 6 0v5M15 13.5A3 3 0 0 1 9 11V9M5 10a7 7 0 0 0 11.5 5.4M19 10a7 7 0 0 1-.5 2.6M12 17v4M8 21h8" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg {...iconProps}>
      <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg {...iconProps}>
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg {...iconProps}>
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9" />
    </svg>
  );
}
