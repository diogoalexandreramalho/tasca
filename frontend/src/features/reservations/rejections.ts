import type { Rejection } from '@/features/reservations/types';

/** Staff-facing explanation for why a sitting can't be booked. */
export const REJECTION_LABEL: Record<Rejection, string> = {
  closed_day: 'Closed on Mondays',
  in_the_past: 'Already started',
  too_soon: 'Less than 1 hour away',
  too_far_ahead: 'More than 60 days ahead',
  party_size_out_of_range: 'Parties of 1 to 8 only',
  fully_booked: 'Fully booked',
};

export function rejectionLabel(reason: string | null | undefined): string {
  return (reason && REJECTION_LABEL[reason as Rejection]) || 'Not available';
}
