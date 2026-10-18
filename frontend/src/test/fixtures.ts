import type { BookingSlot, Reservation } from '@/features/reservations/types';

export const SLOTS: BookingSlot[] = [
  { id: 1, service: 'lunch', start_time: '12:00:00', end_time: '13:30:00' },
  { id: 2, service: 'lunch', start_time: '13:30:00', end_time: '15:00:00' },
  { id: 3, service: 'dinner', start_time: '19:00:00', end_time: '20:30:00' },
  { id: 4, service: 'dinner', start_time: '20:30:00', end_time: '22:00:00' },
];

let nextId = 1;

export function reservation(overrides: {
  slot?: number;
  table?: string;
  name?: string;
  phone?: string;
  party_size?: number;
  notes?: string | null;
  date?: string;
}): Reservation {
  const id = nextId++;
  return {
    id: `00000000-0000-0000-0000-${String(id).padStart(12, '0')}`,
    reservation_date: overrides.date ?? '2026-10-16',
    party_size: overrides.party_size ?? 2,
    status: 'confirmed',
    notes: overrides.notes ?? null,
    customer: {
      id: `c-${id}`,
      name: overrides.name ?? 'Ana Silva',
      phone: overrides.phone ?? '+351912345678',
    },
    table: { id, name: overrides.table ?? 'M1' },
    booking_slot: SLOTS[(overrides.slot ?? 1) - 1]!,
    created_at: '2026-10-14T09:00:00Z',
    updated_at: '2026-10-14T09:00:00Z',
  };
}
