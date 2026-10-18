/** "+351912345678" → "912 345 678". Foreign numbers are shown as stored (E.164). */
export function formatPhone(e164: string): string {
  const pt = /^\+351(\d{3})(\d{3})(\d{3})$/.exec(e164);
  return pt ? `${pt[1]} ${pt[2]} ${pt[3]}` : e164;
}
