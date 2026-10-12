/** Mirrors backend/src/schemas. Times are "HH:MM:SS", dates "YYYY-MM-DD". */

export type Service = 'lunch' | 'dinner';

export type BookingSlot = {
  id: number;
  service: Service;
  start_time: string;
  end_time: string;
};

/** Why a sitting can't be booked (backend `Rejection`). */
export type Rejection =
  | 'party_size_out_of_range'
  | 'closed_day'
  | 'in_the_past'
  | 'too_soon'
  | 'too_far_ahead'
  | 'fully_booked';

export type SlotAvailability = {
  service: Service;
  start_time: string;
  end_time: string;
  available: boolean;
  reason: Rejection | null;
};

export type NewReservation = {
  reservation_date: string;
  start_time: string;
  party_size: number;
  customer_name: string;
  phone: string;
  notes: string | null;
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
