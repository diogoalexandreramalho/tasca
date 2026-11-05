import { useState } from 'react';

import { DateNav } from '@/components/DateNav';
import { CallPanel } from '@/features/calls/CallPanel';
import { Flash, describeBooking } from '@/features/reservations/Flash';
import { NewBookingPanel } from '@/features/reservations/NewBookingPanel';
import { useDayReservations, useSlots } from '@/features/reservations/queries';
import { ReservationRow, plural } from '@/features/reservations/ReservationRow';
import type { BookingSlot, Reservation } from '@/features/reservations/types';
import { formatTime } from '@/lib/dates';
import { usePageParams } from '@/lib/usePageParams';

const SERVICE_LABEL = { lunch: 'Lunch', dinner: 'Dinner' } as const;

function summary(reservations: Reservation[]): string {
  if (reservations.length === 0) return 'No bookings';
  const guests = reservations.reduce((sum, r) => sum + r.party_size, 0);
  return `${plural(reservations.length, 'booking')} · ${plural(guests, 'guest')}`;
}

export function DayViewPage() {
  const { date, today, call, goToDate, openCall, closeCall } = usePageParams();

  const slots = useSlots();
  const reservations = useDayReservations(date);
  const [panelOpen, setPanelOpen] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  function handleCreated(r: Reservation) {
    setPanelOpen(false);
    setFlash(`Booked ${describeBooking(r)}.`);
    goToDate(r.reservation_date);
  }

  function handleCancelled(r: Reservation) {
    setFlash(`Cancelled ${describeBooking(r)}. The table is free again.`);
  }

  const isLoading = slots.isPending || reservations.isPending;
  const error = slots.error ?? reservations.error;

  return (
    <div className="flex flex-col gap-6">
      <DateNav date={date} today={today} onChange={goToDate}>
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
      </DateNav>

      {flash && <Flash message={flash} onDismiss={() => setFlash(null)} />}

      {panelOpen && (
        <NewBookingPanel
          initialDate={date}
          onClose={() => setPanelOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {call && <CallPanel conversationId={call} onClose={closeCall} />}

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
              onOpenCall={openCall}
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
  onOpenCall,
}: {
  slot: BookingSlot;
  reservations: Reservation[];
  onCancelled: (r: Reservation) => void;
  onOpenCall: (conversationId: string) => void;
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
            <ReservationRow
              key={r.id}
              reservation={r}
              onCancelled={onCancelled}
              onOpenCall={onOpenCall}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
