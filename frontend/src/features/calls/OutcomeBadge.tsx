import type { CallOutcome } from '@/features/calls/types';

export const OUTCOME_LABEL: Record<CallOutcome, string> = {
  booked: 'booked',
  cancelled: 'cancelled',
  enquiry: 'question',
  no_action: 'other',
};

const STYLE: Record<CallOutcome, { label: string; className: string }> = {
  booked: { label: 'Booked', className: 'bg-emerald-100 text-emerald-900' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-900' },
  // Tools used but nothing changed: the caller checked availability or their bookings.
  enquiry: { label: 'Question', className: 'bg-azulejo-50 text-azulejo-800' },
  no_action: { label: 'Other', className: 'bg-stone-200 text-stone-700' },
};

export function OutcomeBadge({ outcome }: { outcome: CallOutcome }) {
  const { label, className } = STYLE[outcome];
  return (
    <span className={`whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
