import { useQuery } from '@tanstack/react-query';

import { request } from '@/lib/api';

type Health = { status: string };

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => request<Health>('/health'),
  });
}
