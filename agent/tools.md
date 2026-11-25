# Tools

Four webhook tools call our API (`backend/src/api/v1/endpoints/agent.py`), plus the built-in `end_call` system tool. They're configured in the ElevenLabs dashboard; this file mirrors that configuration.

## Shared settings (all four webhook tools)

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `https://tasca-api-pni4.onrender.com/api/v1/agent/<tool>` (below) |
| Header | `X-Agent-Secret`: workspace secret `tasca_agent_secret` (same value as `AGENT_API_SECRET` in Render) |
| Body | JSON. Every property is **LLM Prompt** (the model fills it), except `conversation_id` |
| Response timeout | the maximum |

`conversation_id` is a **Dynamic Variable** (`system__conversation_id`): ElevenLabs fills it in, the model never sees or chooses it. It links bookings to the call log.

## `check_availability`

**Description**

```text
Check which sittings still have a free table for a date and number of people. Call this before offering any times. Returns "available_times" ("HH:MM"), the only times you may offer. If the list is empty, "reason" says why.
```

**URL:** `/agent/check-availability`. **Body description:** The booking date and number of people the caller asked about.

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | String | yes | Day of the booking in YYYY-MM-DD format, worked out from what the caller said (e.g. "Friday") and today's date. |
| `party_size` | Integer | yes | Number of people, including the caller. |

```json
{"available_times": ["19:00", "20:30"]}
{"available_times": [], "reason": "closed_day"}
```

`reason`: `closed_day`, `fully_booked`, `party_size_out_of_range`, `in_the_past`, `too_far_ahead`.

## `create_reservation`

**Description**

```text
Book a table. Call only after reading all details back and the caller confirmed. Returns "status": booked, already_booked, rejected or invalid. If rejected, "reason" says why; if the reason is fully_booked, the table was just taken and "available_times" lists the times still free that day. If invalid, "field" says what to ask for again.
```

**URL:** `/agent/create-reservation`. **Body description:** The confirmed booking details the caller agreed to.

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | String | yes | Day of the booking in YYYY-MM-DD format. |
| `time` | String (enum `12:00`, `13:30`, `19:00`, `20:30`) | yes | Start time of the chosen sitting, exactly as returned in available_times. |
| `party_size` | Integer | yes | Number of people, including the caller. |
| `name` | String | yes | Name the booking is under, as the caller said it. |
| `phone` | String | yes | Caller's phone number, digits only, e.g. 912345678. |
| `notes` | String | no | Only if the caller mentioned allergies or special requests. Allergies start with "Allergy:", e.g. "Allergy: shellfish (1 person)". |
| `conversation_id` | String, Dynamic Variable `system__conversation_id` | no | Filled automatically. Links the booking to the call log. |

```json
{"status": "booked"}
{"status": "already_booked"}
{"status": "rejected", "reason": "fully_booked", "available_times": ["19:00"]}
{"status": "invalid", "field": "phone"}
```

`already_booked`: the same phone already has a booking for that date and time, so a retry doesn't book twice.

## `find_reservations`

**Description**

```text
Find the caller's upcoming bookings using the phone number the booking was made with. Returns "reservations" (id, date, time, party_size, name). Never read the id aloud. If "field" is "phone", the number is invalid: ask for it again.
```

**URL:** `/agent/find-reservations`. **Body description:** The phone number the caller's booking was made with.

| Property | Type | Required | Description |
|---|---|---|---|
| `phone` | String | yes | Phone number the booking was made with, digits only, e.g. 912345678. |
| `date` | String | no | Only if the caller mentioned a specific day: that day in YYYY-MM-DD format. |

```json
{"reservations": [{"id": "…", "date": "2026-11-27", "time": "20:30", "party_size": 4, "name": "Ana"}]}
{"reservations": [], "field": "phone"}
```

Only the caller's own bookings: the phone is required, and there's no search by name.

## `cancel_reservation`

**Description**

```text
Cancel one booking returned by find_reservations, using its id and the same phone number. Call only after the caller clearly confirmed the cancellation. Returns "status": cancelled, not_found, already_cancelled or too_late.
```

**URL:** `/agent/cancel-reservation`. **Body description:** Which booking to cancel, after the caller clearly confirmed.

| Property | Type | Required | Description |
|---|---|---|---|
| `reservation_id` | String | yes | The id of the booking to cancel, copied exactly from the find_reservations result. Never invent it. |
| `phone` | String | yes | The same phone number used in find_reservations, digits only. |
| `conversation_id` | String, Dynamic Variable `system__conversation_id` | no | Filled automatically. Links the booking to the call log. |

```json
{"status": "cancelled"}
```

`not_found` also covers a booking made with a different phone, so nobody can cancel someone else's booking or learn that it exists.

## `end_call`

Built-in system tool, enabled. No configuration.
