# API Contract Migration Status

Last updated: 2026-04-15

## 7.5 Completion

Legacy wrapped compatibility has been removed from `/api/requests`.

Removed behavior:
- `wrapped=1` response wrapping
- wrapped body payloads in the form `{"request": {...}}`
- admin telemetry endpoints used for wrapped migration tracking

Current behavior:
- API uses canonical request/response contracts only.
- If `wrapped` query param is sent, `/api/requests` endpoints return `400`.
- Wrapped bodies are rejected by schema validation (`extra="forbid"`).

## Notes

- This file is kept as migration history after legacy-path removal.
