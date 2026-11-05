import type { ReactNode } from 'react';

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
          className="rounded-md border border-stone-300 px-2.5 py-1.5 text-sm hover:bg-stone-100"
          aria-label="Previous day"
        >
          ◀
        </button>
        <button
          type="button"
          onClick={() => onChange(addDays(date, 1))}
          className="rounded-md border border-stone-300 px-2.5 py-1.5 text-sm hover:bg-stone-100"
          aria-label="Next day"
        >
          ▶
        </button>
      </div>
      <h1 className="text-xl font-semibold">{formatLongDate(date)}</h1>
      <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
        {date !== today && (
          <button
            type="button"
            onClick={() => onChange(today)}
            className="rounded-md border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
          >
            Today
          </button>
        )}
        <input
          type="date"
          value={date}
          onChange={(e) => isIsoDate(e.target.value) && onChange(e.target.value)}
          className="rounded-md border border-stone-300 px-2 py-1.5 text-sm"
          aria-label="Pick a date"
        />
        {children}
      </div>
    </div>
  );
}
