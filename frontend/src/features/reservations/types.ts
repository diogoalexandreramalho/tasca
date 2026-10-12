/** Mirrors backend/src/schemas. Times are "HH:MM:SS", dates "YYYY-MM-DD". */

export type Service = 'lunch' | 'dinner';

export type BookingSlot = {
  id: number;
  service: Service;
  start_time: string;
  end_time: string;
};

export type Reservation = {
  id: string;
  reservation_date: string;
  party_size: number;
  status: 'confirmed' | 'cancelled';
  notes: string | null;
  customer: { id: string; name: string; phone: string };
  table: { id: number; name: string };
  booking_slot: BookingSlot;
  created_at: string;
  updated_at: string;
};
