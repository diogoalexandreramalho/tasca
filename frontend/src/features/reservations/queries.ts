import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  BookingSlot,
  NewReservation,
  Reservation,
  SlotAvailability,
} from '@/features/reservations/types';
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

export function useAvailability(date: string, partySize: number, enabled: boolean) {
  return useQuery({
    queryKey: ['availability', { date, partySize }],
    queryFn: () =>
      request<SlotAvailability[]>(`/availability?date=${date}&party_size=${partySize}`),
    enabled,
    staleTime: 0, // tables get taken; always ask again
  });
}

export function useCreateReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: NewReservation) =>
      request<Reservation>('/reservations', { method: 'POST', body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['reservations'] });
      void queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });
}
