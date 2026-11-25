import { useEffect, useId, useRef, useState, type FormEvent } from 'react';

import { SidePanel } from '@/components/SidePanel';
import { useAvailability, useCreateReservation } from '@/features/reservations/queries';
import { rejectionLabel } from '@/features/reservations/rejections';
import type { Reservation } from '@/features/reservations/types';
import { ApiError } from '@/lib/api';
import { formatTime, isIsoDate } from '@/lib/dates';

const PARTY_SIZES = [1, 2, 3, 4, 5, 6, 7, 8];
const SERVICE_LABEL = { lunch: 'Lunch', dinner: 'Dinner' } as const;

type Props = {
  initialDate: string;
  onClose: () => void;
  onCreated: (reservation: Reservation) => void;
};

/** Turn an API error into one line for the form. */
function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Could not reach the server.';
  if (error.code === 'booking_rejected') {
    const reason = (error.details as { reason?: string } | undefined)?.reason;
    return `Can't book: ${rejectionLabel(reason).toLowerCase()}.`;
  }
  const fieldErrors = (error.details as { errors?: { field: string; message: string }[] })
    ?.errors;
  if (fieldErrors?.length) {
    return fieldErrors.map((e) => `${e.field}: ${e.message}`).join(' · ');
  }
  return error.message;
}

export function NewBookingPanel({ initialDate, onClose, onCreated }: Props) {
  const hintId = useId();
  const nameHintId = useId();
  const phoneHintId = useId();
  const firstField = useRef<HTMLInputElement>(null);

  const [date, setDate] = useState(initialDate);
  const [partySize, setPartySize] = useState(2);
  const [startTime, setStartTime] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  // After a submit with gaps: show what's missing next to each field.
  const [showMissing, setShowMissing] = useState(false);

  const availability = useAvailability(date, partySize, isIsoDate(date));
  const create = useCreateReservation();

  const slots = availability.data ?? [];
  const allClosedFor = slots.length > 0 && slots.every((s) => !s.available) ? slots[0]!.reason : null;
  const sameReasonEverywhere = allClosedFor !== null && slots.every((s) => s.reason === allClosedFor);

  // Drop the chosen sitting if it stops being available (new date / party size).
  useEffect(() => {
    if (startTime && !slots.some((s) => s.start_time === startTime && s.available)) {
      setStartTime(null);
    }
  }, [slots, startTime]);

  useEffect(() => {
    firstField.current?.focus();
  }, []);

  const missing = {
    sitting: startTime === null,
    name: name.trim() === '',
    phone: phone.trim() === '',
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (startTime === null || missing.name || missing.phone) {
      setShowMissing(true);
      return;
    }
    const reservation = await create
      .mutateAsync({
        reservation_date: date,
        start_time: startTime.slice(0, 5),
        party_size: partySize,
        customer_name: name.trim(),
        phone: phone.trim(),
        notes: notes.trim() || null,
      })
      .catch(() => null); // shown via create.error
    if (reservation) onCreated(reservation);
  }


  return (
    <SidePanel title="New booking" onClose={onClose}>
        <form onSubmit={handleSubmit} noValidate className="flex flex-1 flex-col gap-5 px-5 py-5">
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Date
              <input
                ref={firstField}
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="rounded-md border border-stone-300 px-3 py-2 font-normal"
                required
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Guests
              <select
                value={partySize}
                onChange={(e) => setPartySize(Number(e.target.value))}
                className="rounded-md border border-stone-300 px-3 py-2 font-normal"
              >
                {PARTY_SIZES.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-medium">Sitting</legend>
            {availability.isPending && isIsoDate(date) && (
              <p className="text-sm text-stone-500">Checking availability…</p>
            )}
            {availability.error && (
              <p role="alert" className="text-sm text-red-600">
                {errorMessage(availability.error)}
              </p>
            )}
            {sameReasonEverywhere ? (
              <p className="rounded-md bg-stone-100 px-3 py-2 text-sm text-stone-600">
                {rejectionLabel(allClosedFor)}
              </p>
            ) : (
              slots.map((s) => (
                <label
                  key={s.start_time}
                  className={`flex items-center justify-between rounded-md border px-3 py-2 text-sm ${
                    s.available
                      ? 'cursor-pointer border-stone-300 hover:bg-stone-50 has-[:checked]:border-azulejo-600 has-[:checked]:bg-azulejo-50'
                      : 'cursor-not-allowed border-stone-200 text-stone-400'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="sitting"
                      value={s.start_time}
                      checked={startTime === s.start_time}
                      onChange={() => setStartTime(s.start_time)}
                      disabled={!s.available}
                    />
                    {formatTime(s.start_time)}–{formatTime(s.end_time)} · {SERVICE_LABEL[s.service]}
                  </span>
                  {!s.available && <span>{rejectionLabel(s.reason)}</span>}
                </label>
              ))
            )}
            {showMissing && missing.sitting && !sameReasonEverywhere && (
              <FieldHint>Choose a sitting</FieldHint>
            )}
          </fieldset>

          <div className="flex flex-col gap-1">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={fieldClass(showMissing && missing.name)}
                maxLength={120}
                required
                aria-invalid={showMissing && missing.name}
                aria-describedby={showMissing && missing.name ? nameHintId : undefined}
              />
            </label>
            {showMissing && missing.name && <FieldHint id={nameHintId}>Enter a name</FieldHint>}
          </div>
          <div className="flex flex-col gap-1">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Phone
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="912 345 678"
                className={fieldClass(showMissing && missing.phone)}
                required
                aria-invalid={showMissing && missing.phone}
                aria-describedby={showMissing && missing.phone ? phoneHintId : undefined}
              />
            </label>
            {showMissing && missing.phone && (
              <FieldHint id={phoneHintId}>Enter a phone number</FieldHint>
            )}
          </div>
          <div className="flex flex-col gap-1 text-sm">
            <label className="flex flex-col gap-1 font-medium">
              Notes
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                maxLength={1000}
                className="rounded-md border border-stone-300 px-3 py-2 font-normal"
                aria-describedby={hintId}
              />
            </label>
            <span id={hintId} className="text-stone-500">
              Start allergies with “Allergy:” so they're highlighted.
            </span>
          </div>

          {create.error && (
            <p role="alert" className="text-sm text-red-600">
              {errorMessage(create.error)}
            </p>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-stone-200 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-stone-300 px-4 py-2 text-sm hover:bg-stone-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="rounded-md bg-azulejo-600 hover:bg-azulejo-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {create.isPending ? 'Booking…' : 'Book'}
            </button>
          </div>
        </form>
    </SidePanel>
  );
}

function fieldClass(invalid: boolean): string {
  return `rounded-md border px-3 py-2 font-normal ${invalid ? 'border-red-400' : 'border-stone-300'}`;
}

function FieldHint({ id, children }: { id?: string; children: string }) {
  return (
    <span id={id} className="text-xs text-red-700">
      {children}
    </span>
  );
}
