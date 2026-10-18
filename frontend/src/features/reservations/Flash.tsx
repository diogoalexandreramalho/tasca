/** One-line confirmation after an action ("Booked …", "Cancelled …"). */
export function Flash({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      role="status"
      className="flex items-start justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        className="text-emerald-700 hover:text-emerald-900"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export function describeBooking(r: {
  customer: { name: string };
  party_size: number;
  booking_slot: { start_time: string };
  table: { name: string };
}): string {
  const guests = `${r.party_size} guest${r.party_size === 1 ? '' : 's'}`;
  return `${r.customer.name} · ${guests} · ${r.booking_slot.start_time.slice(0, 5)} at table ${r.table.name}`;
}
