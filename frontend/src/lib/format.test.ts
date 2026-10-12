import { describe, expect, it } from 'vitest';

import { addDays, formatLongDate, formatTime, isIsoDate, todayInLisbon } from '@/lib/dates';
import { formatPhone } from '@/lib/phone';

describe('dates', () => {
  it("uses Lisbon's calendar day, not the browser's", () => {
    // 23:30 UTC on 31 Jul is already 1 Aug in Lisbon (UTC+1 in summer).
    expect(todayInLisbon(new Date('2026-07-31T23:30:00Z'))).toBe('2026-08-01');
  });

  it('adds days across month ends and the October clock change', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01');
    expect(addDays('2026-10-25', -1)).toBe('2026-10-24');
    expect(addDays('2026-10-24', 2)).toBe('2026-10-26');
  });

  it('formats dates and times for display', () => {
    expect(formatLongDate('2026-10-16')).toBe('Friday, 16 October 2026');
    expect(formatTime('20:30:00')).toBe('20:30');
  });

  it('accepts only real YYYY-MM-DD dates', () => {
    expect(isIsoDate('2026-10-16')).toBe(true);
    expect(isIsoDate('16/10/2026')).toBe(false);
    expect(isIsoDate('2026-13-40')).toBe(false);
    expect(isIsoDate(null)).toBe(false);
  });
});

describe('formatPhone', () => {
  it('groups Portuguese numbers and leaves others as stored', () => {
    expect(formatPhone('+351912345678')).toBe('912 345 678');
    expect(formatPhone('+447911123456')).toBe('+447911123456');
  });
});
