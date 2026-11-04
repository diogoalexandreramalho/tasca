import { describe, expect, it } from 'vitest';

import { hasAllergy } from '@/features/reservations/ReservationRow';

describe('hasAllergy', () => {
  it('recognises allergy notes in English and Portuguese', () => {
    expect(hasAllergy('Allergy: shellfish (1 person)')).toBe(true);
    expect(hasAllergy('Alergia: marisco')).toBe(true);
    expect(hasAllergy('allergic to nuts')).toBe(true);
  });

  it('ignores other notes', () => {
    expect(hasAllergy('Birthday, high chair')).toBe(false);
    expect(hasAllergy(null)).toBe(false);
  });
});
