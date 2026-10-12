import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { NewBookingPanel } from '@/features/reservations/NewBookingPanel';
import { useDayReservations, useSlots } from '@/features/reservations/queries';
import type { BookingSlot, Reservation } from '@/features/reservations/types';
import { addDays, formatLongDate, formatTime, isIsoDate, todayInLisbon } from '@/lib/dates';
import { formatPhone } from '@/lib/phone';

const SERVICE_LABEL = { lunch: 'Lunch', dinner: 'Dinner' } as const;

/** Allergies are stored in the notes, starting with "Alergia:" (see backend model). */
export function hasAllergy(notes: string | null): boolean {
  return notes !== null && /alergia|allerg/i.test(notes);
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

function summary(reservations: Reservation[]): string {
  if (reservations.length === 0) return 'No bookings';
  const guests = reservations.reduce((sum, r) => sum + r.party_size, 0);
  return `${plural(reservations.length, 'booking')} · ${plural(guests, 'guest')}`;
}

export function DayViewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const today = todayInLisbon();
  const param = searchParams.get('date');
  const date = isIsoDate(param) ? param : today;

  const slots = useSlots();
  const reservations = useDayReservations(date);
  const [panelOpen, setPanelOpen] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  function goTo(next: string) {
    setSearchParams(next === today ? {} : { date: next });
  }

  function handleCreated(r: Reservation) {
    setPanelOpen(false);
    setFlash(
      `Booked ${r.customer.name} · ${plural(r.party_size, 'guest')} · ` +
        `${formatTime(r.booking_slot.start_time)} at table ${r.table.name}.`,
    );
    goTo(r.reservation_date);
  }

  const isLoading = slots.isPending || reservations.isPending;
  const error = slots.error ?? reservations.error;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => goTo(addDays(date, -1))}
            className="rounded-md border border-stone-300 px-2.5 py-1.5 text-sm hover:bg-stone-100"
            aria-label="Previous day"
          >
            ◀
          </button>
          <button
            type="button"
            onClick={() => goTo(addDays(date, 1))}
            className="rounded-md border border-stone-300 px-2.5 py-1.5 text-sm hover:bg-stone-100"
            aria-label="Next day"
          >
            ▶
          </button>
        </div>
        <h1 className="text-xl font-semibold">{formatLongDate(date)}</h1>
        <div className="flex items-center gap-2 sm:ml-auto">
          {date !== today && (
            <button
              type="button"
              onClick={() => goTo(today)}
              className="rounded-md border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
            >
              Today
            </button>
          )}
          <input
            type="date"
            value={date}
            onChange={(e) => isIsoDate(e.target.value) && goTo(e.target.value)}
            className="rounded-md border border-stone-300 px-2 py-1.5 text-sm"
            aria-label="Pick a date"
          />
          <button
            type="button"
            onClick={() => {
              setFlash(null);
              setPanelOpen(true);
            }}
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-700"
          >
            + New booking
          </button>
        </div>
      </div>

      {flash && (
        <div
          role="status"
          className="flex items-start justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
        >
          <span>{flash}</span>
          <button
            type="button"
            onClick={() => setFlash(null)}
            className="text-emerald-700 hover:text-emerald-900"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {panelOpen && (
        <NewBookingPanel
          initialDate={date}
          onClose={() => setPanelOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {isLoading && <p className="text-sm text-stone-500">Loading bookings…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-600">
          Could not load bookings: {error.message}
        </p>
      )}

      {slots.data && reservations.data && (
        <>
          <p className="text-sm text-stone-600">Whole day: {summary(reservations.data)}</p>
          {slots.data.map((slot) => (
            <SittingSection
              key={slot.id}
              slot={slot}
              reservations={reservations.data.filter((r) => r.booking_slot.id === slot.id)}
            />
          ))}
        </>
      )}
    </div>
  );
}

function SittingSection({ slot, reservations }: { slot: BookingSlot; reservations: Reservation[] }) {
  const title = `${formatTime(slot.start_time)}–${formatTime(slot.end_time)} · ${SERVICE_LABEL[slot.service]}`;

  return (
    <section aria-label={title} className="rounded-lg border border-stone-200 bg-white">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-stone-200 px-4 py-3">
        <h2 className="whitespace-nowrap font-medium">{title}</h2>
        <span className="whitespace-nowrap text-sm text-stone-500">{summary(reservations)}</span>
      </header>
      {reservations.length > 0 && (
        <ul className="divide-y divide-stone-100">
          {reservations.map((r) => (
            <ReservationRow key={r.id} reservation={r} />
          ))}
        </ul>
      )}
    </section>
  );
}

function ReservationRow({ reservation: r }: { reservation: Reservation }) {
  const allergy = hasAllergy(r.notes);

  return (
    <li className="grid grid-cols-[3.5rem_1fr_auto] gap-x-3 gap-y-1 px-4 py-3 text-sm sm:grid-cols-[3.5rem_minmax(8rem,1fr)_5rem_8rem_minmax(8rem,1.5fr)] sm:items-center">
      <span className="font-mono font-medium text-stone-700">{r.table.name}</span>
      <span className="font-medium">{r.customer.name}</span>
      <span className="text-right text-stone-600 sm:text-left">{plural(r.party_size, 'guest')}</span>
      <span className="col-start-2 text-stone-600 sm:col-start-auto">{formatPhone(r.customer.phone)}</span>
      {r.notes && (
        <span
          className={
            allergy
              ? 'col-span-2 col-start-2 rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-900 sm:col-span-1 sm:col-start-auto'
              : 'col-span-2 col-start-2 text-stone-600 sm:col-span-1 sm:col-start-auto'
          }
          data-allergy={allergy || undefined}
        >
          {allergy && <span aria-hidden>⚠ </span>}
          {r.notes}
        </span>
      )}
    </li>
  );
}
