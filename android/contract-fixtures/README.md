# Discair contract fixtures

Phase 0 of [`docs/ANDROID_CLIENT_CONTRACT.md`](../../docs/ANDROID_CLIENT_CONTRACT.md). One recorded response per endpoint the Discair app uses. DTOs are generated from these files, not guessed.

- `librarian/` — Librarian routes (`capture.py`). `navidrome/` — Subsonic calls (`capture_navidrome.py`).
- Each file holds `request`, `response` (`status`, `content_type`, `body`) and `captured_at`. SSE routes store `sse_events` as `{event, data}` in order.
- Lists are cut to 3 items, so shapes are exact but counts are not. Image routes store only the byte count.
- Login passwords, cookies, Navidrome user/token/salt, the server address and signed share tokens are never stored.
- Captured on 2026-10-30 from the Librarian checkout at `332cb16` against a sandbox data directory (slskd disabled, empty music and download folders) and the owner's real Navidrome, read-only. Data in the fixtures is therefore the owner's library and Last.fm / ListenBrainz / MusicBrainz results.
- `tests/test_android_contract_fixtures.py` fails when a fixture's route is no longer served, when a fixture contains credentials, or when a Subsonic fixture loses its envelope.

## Re-capturing

```
NAVIDROME_LIBRARIAN_DATA_DIR=<empty dir> ... uvicorn app.main:app --port 8099   # slskd disabled
python android/contract-fixtures/capture.py http://127.0.0.1:8099 USER PASSWORD
set -a; source config.env; set +a; python android/contract-fixtures/capture_navidrome.py
```

## Not captured

- `POST /api/discovery/{list}/refresh` (spends provider budget) and `POST /api/acquire/queue` (not used in v1).
- Any acquisition with real items: slskd was disabled, so `acquisitions` and the stream are empty snapshots, and Get / track / skip / dismiss show only their refusal shapes (`settings_required`, `409`). Progress item shapes need a safe slskd fixture or are taken from the existing acquisition tests until the owner provides one.
- Deep per-route shape tests. The current test checks routes and hygiene; DTO parsing tests in the Android project will compare against these files.
