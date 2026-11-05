import { Link } from 'react-router';

import { DateNav } from '@/components/DateNav';
import { CallPanel } from '@/features/calls/CallPanel';
import { OutcomeBadge } from '@/features/calls/OutcomeBadge';
import { useCalls } from '@/features/calls/queries';
import type { Call } from '@/features/calls/types';
import { plural } from '@/features/reservations/ReservationRow';
import { formatDuration, formatLisbonClock, formatShortDate, formatTime } from '@/lib/dates';
import { usePageParams } from '@/lib/usePageParams';

/** A day's voice agent calls, newest first. Click one to read it in the side panel. */
export function CallsPage() {
  const { date, today, call, goToDate, openCall, closeCall } = usePageParams();
  const calls = useCalls(date);

  return (
    <div className="flex flex-col gap-6">
      <DateNav date={date} today={today} onChange={goToDate} />

      {calls.isPending && <p className="text-sm text-stone-500">Loading calls…</p>}
      {calls.error && (
        <p role="alert" className="text-sm text-red-600">
          Could not load calls: {calls.error.message}
        </p>
      )}

      {calls.data &&
        (calls.data.length === 0 ? (
          <p className="text-sm text-stone-600">No calls on this day.</p>
        ) : (
          <section aria-label="Calls" className="rounded-lg border border-stone-200 bg-white">
            <header className="border-b border-stone-200 px-4 py-3 text-sm text-stone-500">
              {plural(calls.data.length, 'call')}
            </header>
            <ul className="divide-y divide-stone-100">
              {calls.data.map((c) => (
                <CallRow key={c.id} call={c} onOpen={() => openCall(c.conversation_id)} />
              ))}
            </ul>
          </section>
        ))}

      {call && <CallPanel conversationId={call} onClose={closeCall} />}
    </div>
  );
}

function CallRow({ call: c, onOpen }: { call: Call; onOpen: () => void }) {
  return (
    <li className="px-4 py-3 text-sm">
      <button
        type="button"
        onClick={onOpen}
        className="grid w-full grid-cols-[3rem_3rem_1fr] items-start gap-x-3 gap-y-1 text-left hover:opacity-80 sm:grid-cols-[3rem_3rem_6rem_1fr]"
        aria-label={`Open the call at ${formatLisbonClock(c.started_at)}`}
      >
        <span className="font-medium">{formatLisbonClock(c.started_at)}</span>
        <span className="text-stone-500">{formatDuration(c.duration_secs)}</span>
        <span>
          <OutcomeBadge outcome={c.outcome} />
        </span>
        <span className="col-span-3 line-clamp-2 text-stone-700 sm:col-span-1">
          {c.summary ?? <em className="text-stone-400">Summary removed after 90 days</em>}
        </span>
      </button>
      {c.bookings.length > 0 && (
        <ul className="mt-1 flex flex-col gap-0.5 sm:pl-[12.75rem]">
          {c.bookings.map((b) => (
            <li key={`${b.action}-${b.id}`}>
              <Link
                to={`/?date=${b.reservation_date}`}
                className="text-stone-500 underline-offset-2 hover:text-stone-900 hover:underline"
              >
                {b.action === 'created' ? 'Booked' : 'Cancelled'}{' '}
                {formatShortDate(b.reservation_date)} {formatTime(b.start_time)} ·{' '}
                {plural(b.party_size, 'guest')} · {b.customer_name}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
