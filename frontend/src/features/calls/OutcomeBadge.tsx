import type { CallOutcome } from '@/features/calls/types';

const STYLE: Record<CallOutcome, { label: string; className: string }> = {
  booked: { label: 'Booked', className: 'bg-emerald-100 text-emerald-900' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-900' },
  enquiry: { label: 'Enquiry', className: 'bg-sky-100 text-sky-900' },
  no_action: { label: 'No action', className: 'bg-stone-200 text-stone-700' },
};

export function OutcomeBadge({ outcome }: { outcome: CallOutcome }) {
  const { label, className } = STYLE[outcome];
  return (
    <span className={`whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
