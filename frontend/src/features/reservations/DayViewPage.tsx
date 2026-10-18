import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { Flash, describeBooking } from '@/features/reservations/Flash';
import { NewBookingPanel } from '@/features/reservations/NewBookingPanel';
import { useDayReservations, useSlots } from '@/features/reservations/queries';
import { ReservationRow, plural } from '@/features/reservations/ReservationRow';
import type { BookingSlot, Reservation } from '@/features/reservations/types';
import { addDays, formatLongDate, formatTime, isIsoDate, todayInLisbon } from '@/lib/dates';

const SERVICE_LABEL = { lunch: 'Lunch', dinner: 'Dinner' } as const;

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
    setFlash(`Booked ${describeBooking(r)}.`);
    goTo(r.reservation_date);
  }

  function handleCancelled(r: Reservation) {
    setFlash(`Cancelled ${describeBooking(r)}. The table is free again.`);
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
        <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
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
            className="whitespace-nowrap rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-700"
          >
            + New booking
          </button>
        </div>
      </div>

      {flash && <Flash message={flash} onDismiss={() => setFlash(null)} />}

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
              onCancelled={handleCancelled}
            />
          ))}
        </>
      )}
    </div>
  );
}

function SittingSection({
  slot,
  reservations,
  onCancelled,
}: {
  slot: BookingSlot;
  reservations: Reservation[];
  onCancelled: (r: Reservation) => void;
}) {
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
            <ReservationRow key={r.id} reservation={r} onCancelled={onCancelled} />
          ))}
        </ul>
      )}
    </section>
  );
}
