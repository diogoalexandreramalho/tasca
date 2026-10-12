import { useQuery } from '@tanstack/react-query';

import { request } from '@/lib/api';

export type BookingSlot = {
  id: number;
  service: 'lunch' | 'dinner';
  start_time: string;
  end_time: string;
};

export function useSlots() {
  return useQuery({
    queryKey: ['slots'],
    queryFn: () => request<BookingSlot[]>('/slots'),
  });
}
