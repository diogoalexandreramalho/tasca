import { useState } from 'react';
import { Link } from 'react-router';

import { useCancelReservation } from '@/features/reservations/queries';
import type { Reservation } from '@/features/reservations/types';
import { ApiError } from '@/lib/api';
import { formatShortDate, formatTime, hasStarted } from '@/lib/dates';
import { formatPhone } from '@/lib/phone';

/** Allergies are stored in the notes, starting with "Alergia:" (see backend model). */
export function hasAllergy(notes: string | null): boolean {
  return notes !== null && /alergia|allerg/i.test(notes);
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

type Props = {
  reservation: Reservation;
  /** Show the date and sitting (search results); the day view groups by them instead. */
  showWhen?: boolean;
  onCancelled: (reservation: Reservation) => void;
};

export function ReservationRow({ reservation: r, showWhen = false, onCancelled }: Props) {
  const allergy = hasAllergy(r.notes);
  const cancel = useCancelReservation();
  const [confirming, setConfirming] = useState(false);
  const canCancel = !hasStarted(r.reservation_date, r.booking_slot.start_time);

  async function confirmCancel() {
    const cancelled = await cancel.mutateAsync(r.id).catch(() => null);
    if (cancelled) onCancelled(cancelled);
  }

  return (
    <li className="px-4 py-3 text-sm">
      <div
        className={`grid gap-x-3 gap-y-1 sm:items-center ${
          showWhen
            ? 'grid-cols-[7.5rem_1fr_auto] sm:grid-cols-[7.5rem_minmax(8rem,1fr)_5rem_8rem_minmax(8rem,1.5fr)_5.5rem]'
            : 'grid-cols-[4rem_1fr_auto] sm:grid-cols-[4rem_minmax(8rem,1fr)_5rem_8rem_minmax(8rem,1.5fr)_5.5rem]'
        }`}
      >
        <span className="font-mono font-medium text-stone-700">
          {showWhen && (
            <Link
              to={`/?date=${r.reservation_date}`}
              className="block whitespace-nowrap font-sans font-normal text-stone-500 hover:text-stone-900 hover:underline"
              title="Open this day"
            >
              {formatShortDate(r.reservation_date)} · {formatTime(r.booking_slot.start_time)}
            </Link>
          )}
          {r.table.name}
        </span>
        <span className="font-medium">{r.customer.name}</span>
        <span className="text-right text-stone-600 sm:text-left">{plural(r.party_size, 'guest')}</span>
        <span className="col-start-2 text-stone-600 sm:col-start-auto">
          {formatPhone(r.customer.phone)}
        </span>
        <span
          className={`col-span-2 col-start-2 sm:col-span-1 sm:col-start-auto ${
            allergy
              ? 'rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-900'
              : 'text-stone-600'
          } ${r.notes ? '' : 'hidden sm:block'}`}
          data-allergy={allergy || undefined}
        >
          {allergy && <span aria-hidden>⚠ </span>}
          {r.notes}
        </span>
        <span className="col-start-2 sm:col-start-auto sm:text-right">
          {canCancel && !confirming && (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="text-stone-500 underline-offset-2 hover:text-red-700 hover:underline"
              aria-label={`Cancel booking for ${r.customer.name}`}
            >
              Cancel
            </button>
          )}
        </span>
      </div>

      {confirming && (
        <div
          role="group"
          aria-label="Confirm cancellation"
          className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-red-50 px-3 py-2"
        >
          <span className="text-red-900">
            Cancel {r.customer.name}'s booking ({formatShortDate(r.reservation_date)},{' '}
            {formatTime(r.booking_slot.start_time)}, {r.table.name})?
          </span>
          <span className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={() => {
                setConfirming(false);
                cancel.reset();
              }}
              className="rounded-md border border-stone-300 bg-white px-3 py-1 hover:bg-stone-100"
            >
              Keep
            </button>
            <button
              type="button"
              onClick={confirmCancel}
              disabled={cancel.isPending}
              className="rounded-md bg-red-700 px-3 py-1 font-medium text-white hover:bg-red-800 disabled:opacity-50"
            >
              {cancel.isPending ? 'Cancelling…' : 'Yes, cancel'}
            </button>
          </span>
          {cancel.error && (
            <p role="alert" className="w-full text-red-700">
              {cancel.error instanceof ApiError ? cancel.error.message : 'Could not reach the server.'}
            </p>
          )}
        </div>
      )}
    </li>
  );
}
