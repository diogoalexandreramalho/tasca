/** Mirrors backend/src/schemas/call.py. */

export type CallOutcome = 'booked' | 'cancelled' | 'enquiry' | 'no_action';

export type CallBooking = {
  id: string;
  action: 'created' | 'cancelled';
  reservation_date: string;
  start_time: string;
  party_size: number;
  customer_name: string;
  status: 'confirmed' | 'cancelled';
};

export type Call = {
  id: string;
  conversation_id: string;
  started_at: string;
  duration_secs: number;
  outcome: CallOutcome;
  summary: string | null; // null once removed after 90 days
  bookings: CallBooking[];
};

export type TranscriptLine = {
  role: 'agent' | 'user';
  message: string;
  time_in_call_secs: number;
};

export type CallDetail = Call & { transcript: TranscriptLine[] | null };
