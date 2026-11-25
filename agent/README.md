# Voice agent

The agent runs on ElevenLabs Agents (speech-to-text, LLM, text-to-speech). It's configured in the ElevenLabs dashboard, not in code; this folder mirrors that configuration so it can be reviewed and versioned.

- [`prompt.md`](prompt.md): first message and system prompt
- [`tools.md`](tools.md): the four webhook tools that call our API, plus `end_call`

## How it fits together

```
Customer website ──POST /voice/session──► API ──► ElevenLabs: one-time WebRTC token
      │
      └── browser ◄──── voice (WebRTC) ────► ElevenLabs agent
                                                 │  tools: POST /agent/… (X-Agent-Secret)
                                                 ▼
                                                API ──► Postgres
                                                 ▲
      call ends ── post-call webhook (signed) ───┘ ──► Calls page in the dashboard
```

The agent never states a fact a tool didn't return: availability, bookings and outcomes all come from the API, which applies the same booking rules as the dashboard (`backend/src/services/booking_rules.py`). The few fixed facts in the prompt (opening days, sittings, party sizes, booking window) match those rules.

## Dashboard settings that matter

| Setting | Value | Why |
|---|---|---|
| Language | English | Portfolio audience; the restaurant stays in Lisbon |
| Timezone | Europe/Lisbon | So "tomorrow" and "Friday" resolve to the right date |
| Authentication | On, no allowlist | The agent is private: a conversation needs a one-time token from `POST /voice/session` |
| Max conversation duration | 180 s | Caps the cost of each conversation |
| Call limits: daily limit | 5 | Caps the cost per day; Preview tests count too |
| Overrides | All off | The browser can't change the prompt, voice, duration or anything else |
| Post-call webhook | `POST /api/v1/webhooks/elevenlabs/post-call`, transcript events, HMAC secret | Fills the call log; verified with `ELEVENLABS_WEBHOOK_SECRET` |
| API key `tasca-api` | ElevenAgents access only | Used by the API to get conversation tokens (needs `convai_write`) |

Secrets live only in Render, ElevenLabs and a password manager. None are in this repo.

## Changing the agent

1. Change it in the ElevenLabs dashboard and publish.
2. Update `prompt.md` / `tools.md` to match, in the same PR as any backend change it depends on.
3. If the booking rules change, update `booking_rules.py`, the prompt's "What you know" section and the website footer together.
