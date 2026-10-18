/**
 * Calendar dates as "YYYY-MM-DD" strings. "Today" is the restaurant's today
 * (Lisbon), not the browser's, so staff abroad still see the right day.
 */

const RESTAURANT_TZ = 'Europe/Lisbon';

export function todayInLisbon(now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone: RESTAURANT_TZ }).format(now);
}

/** Current wall-clock time in Lisbon as "YYYY-MM-DDTHH:MM" (sortable as a string). */
export function nowInLisbon(now: Date = new Date()): string {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: RESTAURANT_TZ,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    })
      .formatToParts(now)
      .map((p) => [p.type, p.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

/** Has a sitting on `isoDate` starting at `startTime` ("HH:MM[:SS]") begun, in Lisbon? */
export function hasStarted(isoDate: string, startTime: string, now: Date = new Date()): boolean {
  return `${isoDate}T${startTime.slice(0, 5)}` <= nowInLisbon(now);
}

/** "Fri 16 Oct" */
export function formatShortDate(isoDate: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(`${isoDate}T00:00:00Z`));
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
