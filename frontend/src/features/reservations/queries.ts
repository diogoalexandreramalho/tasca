import { useQuery } from '@tanstack/react-query';

import type { BookingSlot, Reservation } from '@/features/reservations/types';
import { request } from '@/lib/api';

export function useSlots() {
  return useQuery({
    queryKey: ['slots'],
    queryFn: () => request<BookingSlot[]>('/slots'),
    staleTime: Infinity, // fixed sittings; they don't change during a session
  });
}

export function useDayReservations(date: string) {
  return useQuery({
    queryKey: ['reservations', { date }],
    queryFn: () => request<Reservation[]>(`/reservations?date=${date}`),
  });
}
