# CritiqueBrainz Inline Album Reviews (`CB.md`)

**Status:** Implemented across server and all three clients (CB-1–CB-5 merged); web MBID forwarding correction in progress
**Created:** 2026-11-23
**Scope:** Server (`integrations/critiquebrainz/`, `app/services/`, `app/api/metadata.py`) and clients (Web, macOS, Android)

---

## 1. Goal

Display full-text, Creative Commons–licensed CritiqueBrainz reviews inline in the Album page **Reviews** tab, **above** the existing Pitchfork / The Guardian / WordPress blurbs and links.

- **Languages:** English (`en`), French (`fr`), and Arabic (`ar`), whenever available.
- **No hard count limit:** Fetch all eligible CritiqueBrainz reviews for the album's release-group MBID.
- **Single-review view with cycling chevron:** Show one CritiqueBrainz review at a time with a chevron control to advance to the next review, cycling through all available eligible reviews (mirroring the "Another booklet" cycling pattern).
- **Readability formatting:** If a review's original text has no paragraph breaks, insert paragraph breaks approximately every **90 words** at the closest sentence-ending punctuation (`.`, `!`, `?`, `؟`).
- **Press blurbs below:** Pitchfork, The Guardian, and WordPress blurbs and links continue to display below the CritiqueBrainz block when available (unchanged `MAX_REVIEWS = 3` cap).

---

## 2. Artist Reviews Probe (Out of Scope)

A live probe of `https://critiquebrainz.org/ws/1/review/` on 2026-11-23 showed:

| Entity type | Total | `en` | `fr` | `ar` |
|---|---:|---:|---:|---:|
| `release_group` (Albums) | 13,093 | 12,122 | 673 | 3 |
| `artist` | 635 | 563 | 16 | 0 |

Sampled top artist reviews had low editorial signal (one-line fan comments, PR blurbs, max 2 upvotes) and >99.9% of artists would have an empty tab. **Decision:** Do not add a "Reviews" tab to Artist pages; scope CritiqueBrainz strictly to Album pages (`release_group`).

---

## 3. Server Design

### 3.1 Provider Client — `integrations/critiquebrainz/reviews.py` (new)
- Pure HTTP `get` callable injection (no `app/` imports, no `navidrome_server.py` edits per D-016).
- **Endpoint:** `GET https://critiquebrainz.org/ws/1/review/`
  - Params: `entity_id={mbid}`, `entity_type=release_group`, `sort=popularity`, `limit=50`, `offset={offset}`.
  - Paginate while `offset + limit < count` (with a polite safety ceiling, e.g. 5 pages / 250 raw reviews, to prevent runaway requests on outliers) under the route's existing deadline.
  - Descriptive `User-Agent` header; `REVIEW_PAGE_TIMEOUT` (4.0 s total, 1.5 s connect).
- **Eligibility filter:**
  - `language in {"en", "fr", "ar"}`
  - `is_draft` is false and `is_hidden` is false
  - Non-empty `text` (after trimming whitespace, minimum 40 characters to skip rating-only or stub entries).
- **Ordering:**
  - Group/prioritize by popularity descending (tie-break: `source == "BBC"` first, then `published_on` descending), keeping all eligible reviews across `en`, `fr`, `ar`.
- **Paragraph reflow (server-side, pure function):**
  - Normalize `\r\n` → `\n` and collapse 3+ newlines to `\n\n`.
  - If the text already contains paragraph breaks (`\n\n` or multiple non-empty lines), preserve them.
  - If the text is a single unbroken block of > 90 words, split into paragraphs targeting **90 words** per paragraph by choosing the sentence boundary (`.`, `!`, `?`, `؟` followed by whitespace) closest to the 90-word mark from the start of the current paragraph. If no sentence boundary exists within a reasonable window (e.g. ±35 words), fall back to the nearest whitespace at 90 words.
- **Output shape per CritiqueBrainz review:**
  ```json
  {
    "id": "c807d0b4-0dd0-43fe-a7c4-d29bb61f389e",
    "source": "CritiqueBrainz",
    "origin": "BBC",
    "full_text": "Paragraph one...\n\nParagraph two...",
    "paragraphs": ["Paragraph one...", "Paragraph two..."],
    "quote": "First 1-2 sentences fallback...",
    "url": "https://critiquebrainz.org/review/c807d0b4-0dd0-43fe-a7c4-d29bb61f389e",
    "language": "en",
    "author": "Display Name",
    "rating": 5,
    "license": "CC BY-SA 3.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
    "published_on": "2022-10-17"
  }
  ```

### 3.2 Review Pipeline & API Contract
- **Route (`app/api/metadata.py`):**
  - Extend `GET /api/album-reviews` to accept optional `mbid: str = ""` (matching `GET /api/album-links`).
  - When `mbid` is omitted or empty, skip CritiqueBrainz cleanly (zero extra MusicBrainz lookups on the hot path).
- **Response shape (backward-compatible):**
  ```json
  {
    "critiquebrainz": [ ... ],
    "reviews": [
      { "source": "Pitchfork", "quote": "...", "url": "https://..." }
    ]
  }
  ```
  - Keeping `critiquebrainz` as its own top-level array alongside `reviews` cleanly separates the full-text cycling block from the existing press-blurb list, preserves the `MAX_REVIEWS = 3` cap for Pitchfork/Guardian/WordPress, and avoids breaking older clients that only read `reviews`.
- **Caching, Staleness & Failure Marks (`app/services/album_review_sources.py`):**
  - Store key: `album-review-source:v1:CritiqueBrainz:{mbid}` (`SOURCE_FOUND_TTL = 30d`, `SOURCE_MISS_TTL = 3d`).
  - Failure mark (K4): `album-review-source-failed:v1:CritiqueBrainz:{mbid}` (`SOURCE_FAILURE_TTL = 1h`).
  - K2 stale serving: serves stale CritiqueBrainz rows up to 70 days with background refresh and `fetched_at`.
  - List cache key: include `mbid` when present (`album-reviews:v2:{artist}:{album}:{mbid}`) so MBID-aware answers do not collide with legacy name-only entries.
  - `runtime_metrics.py`: register `critiquebrainz.org` in the fixed host table under `reviews`.
  - `owned_prefetch.py`: when `reviews` cap is enabled and the owned album has a release-group MBID, prefetch CritiqueBrainz through the same helper.

---

## 4. Client Design (Web, macOS, Android)

All three clients follow the same presentation rules (domain formatting stays server-side):

1. **Request:** Pass `mbid` to `GET /api/album-reviews?artist=...&album=...&mbid=...` whenever the album page has a release-group MBID.
2. **Placement:** In the Album page **Reviews** tab, render the CritiqueBrainz block **at the top**, above the Pitchfork / The Guardian / WordPress blurbs. If `critiquebrainz` is empty, render nothing above the press blurbs (no empty state).
3. **Single-review display + Cycling Chevron:**
   - Display `critiquebrainz[index]` (starting at `0`).
   - When `critiquebrainz.length > 1`, show a **chevron button** (`›`) with an accessible label (e.g., `"Next review"` / `"Review 1 of 4"`) and counter (`1 / N`). Clicking/tapping advances `index = (index + 1) % critiquebrainz.length`, cycling through all eligible reviews.
   - Respect `prefers-reduced-motion` (no looping animations; instant or subtle swap).
4. **Typography, Language & RTL:**
   - Render `paragraphs` as distinct `<p>` / text blocks.
   - Show a compact language badge (`EN`, `FR`, `AR`) and optional `origin` (e.g. `BBC`) when present.
   - When `language == "ar"`, apply right-to-left text direction (`dir="rtl"` on Web, `.environment(\.layoutDirection, .rightToLeft)` on macOS, `LayoutDirection.Rtl` on Android).
5. **Attribution Footer (CC license compliance):**
   - Author (`author`), optional rating (`4/5`), clickable license link (`license` → `license_url`), and link to the original CritiqueBrainz page (`url`).
6. **Press Blurbs Below:**
   - Render existing `reviews` (Pitchfork, The Guardian, WordPress) below a subtle divider/section heading whenever `reviews` is non-empty.

---

## 5. Phased Implementation Slices

| Slice | Scope | Verification |
|---|---|---|
| **CB-1** | `integrations/critiquebrainz/reviews.py`: API client, pagination, `en`/`fr`/`ar` filter, 90-word sentence-boundary paragraph reflow, unit tests (`tests/test_critiquebrainz_reviews.py`), `docs/ARCHITECTURE.md` row. | `pytest tests/test_critiquebrainz_reviews.py` |
| **CB-2** | Server wiring: `album_review_sources.py`, `app/api/metadata.py` (`mbid` param + `critiquebrainz` field), `runtime_metrics.py`, `owned_prefetch.py`, integration tests. | `pytest tests/test_album_reviews.py tests/test_album_page_sources.py` |
| **CB-3** | Web client: pass `mbid`, render CritiqueBrainz block above press blurbs with cycling chevron, RTL support, and CC attribution (Listening Room + existing themes). | Local UI check (`docs/LOCAL_UI_TESTING.md`) |
| **CB-4** | macOS client: pass `mbid`, render CritiqueBrainz block above press blurbs in Album Reviews tab with cycling chevron (matching Booklet cycling), RTL support, CC attribution. | Focused `swift test --filter ...` |
| **CB-5** | Android client: pass `mbid`, render CritiqueBrainz block above press blurbs across themes with cycling chevron, RTL support, CC attribution. | Focused Gradle unit tests |


### Implementation and verification status (2026-11-23)

- CB-1 through CB-5 are implemented and merged in PRs [#1240](https://github.com/abucalip/navi-librarian/pull/1240), [#1241](https://github.com/abucalip/navi-librarian/pull/1241), [#1242](https://github.com/abucalip/navi-librarian/pull/1242), [#1243](https://github.com/abucalip/navi-librarian/pull/1243), and [#1244](https://github.com/abucalip/navi-librarian/pull/1244).
- Cross-client verification found two identifier defects: web read nonexistent `album.mbid` instead of `release_group_mbid`; macOS used Navidrome's album `musicBrainzId` (a release MBID) instead of the album page's release-group MBID. Android already reads the correct field. PR [#1245](https://github.com/abucalip/navi-librarian/pull/1245) now fixes both and adds regression coverage. Initial GitHub Actions passed on web-only head `2affb063ddeacc7d6be979604fff03d877997d3d`; macOS Swift tests and manual browser verification remain outstanding.
- Bitches Brew (release group `a9e30282-5b37-3f92-b897-b9659a1a312b`) has no CritiqueBrainz review, so its empty result is expected and it is not a valid positive smoke test. A positive control is Tupelo Honey by Van Morrison (release group `c2c0e5e7-dc91-3e4e-b5bf-a26f06328926`), which has one CritiqueBrainz review by Chris Jones.
- Provider runtime verification and client UI verification remain separate from implementation and automated tests; do not infer deployment or runtime success from merged code.
