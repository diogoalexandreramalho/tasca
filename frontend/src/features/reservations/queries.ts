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

export type SearchBy = { phone: string; name?: never } | { name: string; phone?: never };

/** A query that looks like a phone number searches by phone, anything else by name. */
export function searchParamsFor(query: string): SearchBy | null {
  const q = query.trim();
  if (!q) return null;
  const digits = q.replace(/\D/g, '');
  return /^[+\d\s().-]+$/.test(q) && digits.length >= 6 ? { phone: q } : { name: q };
}

export function useSearchReservations(query: string) {
  const params = searchParamsFor(query);
  return useQuery({
    queryKey: ['reservations', { search: params }],
    queryFn: () => {
      const qs = new URLSearchParams(
        params?.phone !== undefined ? { phone: params.phone } : { name: params?.name ?? '' },
      );
      return request<Reservation[]>(`/reservations?${qs}`);
    },
    enabled: params !== null,
  });
}

export function useCancelReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      request<Reservation>(`/reservations/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['reservations'] });
      void queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
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
