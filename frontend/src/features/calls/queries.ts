import { useQuery } from '@tanstack/react-query';

import type { Call, CallDetail } from '@/features/calls/types';
import { request } from '@/lib/api';

export function useCalls(date: string) {
  return useQuery({
    queryKey: ['calls', { date }],
    queryFn: () => request<Call[]>(`/calls?date=${date}`),
  });
}

/** Bookings know the conversation id, so the panel always opens a call by it. */
export function useCall(conversationId: string) {
  return useQuery({
    queryKey: ['calls', 'by-conversation', conversationId],
    queryFn: () =>
      request<CallDetail>(`/calls/by-conversation/${encodeURIComponent(conversationId)}`),
  });
}
