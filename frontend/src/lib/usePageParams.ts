import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { isIsoDate, todayInLisbon } from '@/lib/dates';

/**
 * The page's state that lives in the URL, so reloads and shared links keep it:
 * - `date`: the day shown (omitted when it's today in Lisbon)
 * - `call`: the conversation id of the call open in the side panel, if any
 */
export function usePageParams() {
  const [params, setParams] = useSearchParams();
  const today = todayInLisbon();
  const raw = params.get('date');
  const date = isIsoDate(raw) ? raw : today;
  const call = params.get('call');

  const update = useCallback(
    (next: { date?: string; call?: string | null }, replace = false) => {
      setParams(
        (current) => {
          const p = new URLSearchParams(current);
          if (next.date !== undefined) {
            if (next.date === today) p.delete('date');
            else p.set('date', next.date);
          }
          if (next.call !== undefined) {
            if (next.call === null) p.delete('call');
            else p.set('call', next.call);
          }
          return p;
        },
        { replace },
      );
    },
    [setParams, today],
  );

  return {
    date,
    today,
    call,
    goToDate: (d: string) => update({ date: d, call: null }),
    openCall: (conversationId: string) => update({ call: conversationId }),
    // Replace rather than push, so Back doesn't reopen what was just closed.
    closeCall: () => update({ call: null }, true),
  };
}
