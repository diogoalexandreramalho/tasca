import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { Flash, describeBooking } from '@/features/reservations/Flash';
import { searchParamsFor, useSearchReservations } from '@/features/reservations/queries';
import { ReservationRow, plural } from '@/features/reservations/ReservationRow';
import type { Reservation } from '@/features/reservations/types';

export function SearchPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
  const by = searchParamsFor(query);
  const results = useSearchReservations(query);
  const [flash, setFlash] = useState<string | null>(null);

  function handleCancelled(r: Reservation) {
    setFlash(`Cancelled ${describeBooking(r)}. The table is free again.`);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/" className="text-sm text-stone-500 hover:text-stone-900">
          ← Back to the day view
        </Link>
        <h1 className="mt-2 text-xl font-semibold">
          {by ? `Upcoming bookings for “${query.trim()}”` : 'Search bookings'}
        </h1>
        {by && (
          <p className="mt-1 text-sm text-stone-600">
            {by.phone ? 'Matching this phone number.' : 'Names containing this text, on any date.'}
          </p>
        )}
      </div>

      {flash && <Flash message={flash} onDismiss={() => setFlash(null)} />}

      {!by && (
        <p className="text-sm text-stone-600">Type a name or a phone number in the search box.</p>
      )}
      {by && results.isPending && <p className="text-sm text-stone-500">Searching…</p>}
      {results.error && (
        <p role="alert" className="text-sm text-red-600">
          {results.error.message}
        </p>
      )}

      {results.data &&
        (results.data.length === 0 ? (
          <p className="text-sm text-stone-600">No upcoming bookings found.</p>
        ) : (
          <section
            aria-label="Search results"
            className="rounded-lg border border-stone-200 bg-white"
          >
            <header className="border-b border-stone-200 px-4 py-3 text-sm text-stone-500">
              {plural(results.data.length, 'booking')}
            </header>
            <ul className="divide-y divide-stone-100">
              {results.data.map((r) => (
                <ReservationRow key={r.id} reservation={r} showWhen onCancelled={handleCancelled} />
              ))}
            </ul>
          </section>
        ))}
    </div>
  );
}
