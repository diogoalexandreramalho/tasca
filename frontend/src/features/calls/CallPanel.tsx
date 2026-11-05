import { Link } from 'react-router';

import { SidePanel } from '@/components/SidePanel';
import { OutcomeBadge } from '@/features/calls/OutcomeBadge';
import { useCall } from '@/features/calls/queries';
import type { CallBooking, CallDetail, TranscriptLine } from '@/features/calls/types';
import { plural } from '@/features/reservations/ReservationRow';
import { ApiError } from '@/lib/api';
import {
  formatDuration,
  formatLisbonClock,
  formatLongDate,
  formatShortDate,
  formatTime,
  lisbonDateOf,
} from '@/lib/dates';

type Props = { conversationId: string; onClose: () => void };

/** One call: when, how long, outcome, summary, the bookings it touched, the conversation. */
export function CallPanel({ conversationId, onClose }: Props) {
  const call = useCall(conversationId);

  return (
    <SidePanel title="Call" onClose={onClose}>
      <div className="flex flex-col gap-6 px-5 py-5 text-sm">
        {call.isPending && <p className="text-stone-500">Loading call…</p>}
        {call.error && (
          <p role="alert" className="text-red-600">
            {call.error instanceof ApiError && call.error.status === 404
              ? 'This call hasn’t been recorded (yet).'
              : `Could not load the call: ${call.error.message}`}
          </p>
        )}
        {call.data && <CallBody call={call.data} />}
      </div>
    </SidePanel>
  );
}

function CallBody({ call }: { call: CallDetail }) {
  const removed = call.summary === null && call.transcript === null;

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-medium">
          {formatLongDate(lisbonDateOf(call.started_at))}, {formatLisbonClock(call.started_at)}
        </span>
        <span className="text-stone-500">{formatDuration(call.duration_secs)}</span>
        <OutcomeBadge outcome={call.outcome} />
      </div>

      {removed ? (
        <p className="rounded-md bg-stone-100 px-3 py-2 text-stone-600">
          Summary and conversation removed after 90 days.
        </p>
      ) : (
        call.summary && (
          <section aria-label="Summary">
            <h3 className="mb-1 font-medium">Summary</h3>
            <p className="text-stone-700">{call.summary}</p>
          </section>
        )
      )}

      {call.bookings.length > 0 && (
        <section aria-label="Bookings from this call">
          <h3 className="mb-2 font-medium">Bookings from this call</h3>
          <ul className="flex flex-col gap-2">
            {call.bookings.map((b) => (
              <BookingLine key={`${b.action}-${b.id}`} booking={b} />
            ))}
          </ul>
        </section>
      )}

      {call.transcript && call.transcript.length > 0 && (
        <section aria-label="Conversation">
          <h3 className="mb-2 font-medium">Conversation</h3>
          <ol className="flex flex-col gap-2">
            {call.transcript.map((line, i) => (
              <TranscriptBubble key={i} line={line} />
            ))}
          </ol>
        </section>
      )}
    </>
  );
}

function BookingLine({ booking: b }: { booking: CallBooking }) {
  const changedLater = b.action === 'created' && b.status === 'cancelled';
  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-stone-200 px-3 py-2">
      <span className="font-medium">{b.action === 'created' ? 'Booked' : 'Cancelled'}</span>
      <span>
        {formatShortDate(b.reservation_date)} · {formatTime(b.start_time)} ·{' '}
        {plural(b.party_size, 'guest')} · {b.customer_name}
      </span>
      {changedLater && <span className="text-stone-500">(cancelled later)</span>}
      <Link
        to={`/?date=${b.reservation_date}`}
        className="ml-auto text-stone-500 underline-offset-2 hover:text-stone-900 hover:underline"
      >
        Open day
      </Link>
    </li>
  );
}

function TranscriptBubble({ line }: { line: TranscriptLine }) {
  const isAgent = line.role === 'agent';
  return (
    <li className={`flex flex-col ${isAgent ? 'items-start' : 'items-end'}`}>
      <span className="mb-0.5 text-xs text-stone-500">
        {isAgent ? 'Agent' : 'Caller'} · {formatDuration(line.time_in_call_secs)}
      </span>
      <span
        className={`max-w-[85%] rounded-lg px-3 py-2 ${
          isAgent ? 'bg-stone-100 text-stone-900' : 'bg-stone-900 text-white'
        }`}
      >
        {line.message}
      </span>
    </li>
  );
}
