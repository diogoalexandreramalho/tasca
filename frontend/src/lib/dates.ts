/**
 * Calendar dates as "YYYY-MM-DD" strings. "Today" is the restaurant's today
 * (Lisbon), not the browser's, so staff abroad still see the right day.
 */

const RESTAURANT_TZ = 'Europe/Lisbon';

export function todayInLisbon(now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone: RESTAURANT_TZ }).format(now);
}

export function isIsoDate(value: string | null): value is string {
  return value !== null && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

/** Shift a date by whole days. Done in UTC so DST changes can't skip or repeat a day. */
export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** "Friday, 16 October 2026" */
export function formatLongDate(isoDate: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${isoDate}T00:00:00Z`));
}

/** "20:30:00" → "20:30" */
export function formatTime(time: string): string {
  return time.slice(0, 5);
}
