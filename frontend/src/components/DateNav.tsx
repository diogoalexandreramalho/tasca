import type { ReactNode } from 'react';

import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';
import { addDays, formatLongDate, isIsoDate } from '@/lib/dates';

type Props = {
  date: string;
  today: string;
  onChange: (date: string) => void;
  /** Extra actions on the right, e.g. "+ New booking". */
  children?: ReactNode;
};

/** ◀ ▶ arrows, the spelled-out date, "Today" and a date picker. */
export function DateNav({ date, today, onChange, children }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onChange(addDays(date, -1))}
          className="flex size-11 items-center justify-center rounded-md border border-stone-300 bg-white text-azulejo-800 hover:bg-stone-100 sm:size-8"
          aria-label="Previous day"
        >
          <ChevronLeftIcon />
        </button>
        <button
          type="button"
          onClick={() => onChange(addDays(date, 1))}
          className="flex size-11 items-center justify-center rounded-md border border-stone-300 bg-white text-azulejo-800 hover:bg-stone-100 sm:size-8"
          aria-label="Next day"
        >
          <ChevronRightIcon />
        </button>
      </div>
      <h1 className="text-xl font-semibold">{formatLongDate(date)}</h1>
      <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
        {date !== today && (
          <button
            type="button"
            onClick={() => onChange(today)}
            className="h-11 rounded-md border border-stone-300 bg-white px-3 text-sm hover:bg-stone-100 sm:h-auto sm:py-1.5"
          >
            Today
          </button>
        )}
        <input
          type="date"
          value={date}
          onChange={(e) => isIsoDate(e.target.value) && onChange(e.target.value)}
          className="h-11 rounded-md border border-stone-300 bg-white px-2 text-sm sm:h-auto sm:py-1.5"
          aria-label="Pick a date"
        />
        {children}
      </div>
    </div>
  );
}
