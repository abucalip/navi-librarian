# Star Operation: clearer reasons, richer feedback, stars as seeds, a discovery mode (proposal)

Status: **proposal, not approved.** Nothing here is built, and nothing is added to `REQUIREMENTS.md` or `DECISIONS.md` until the owner approves a slice. Drafted 2026-11-15 against `main` at `ccd8e5d`.

## 1. Why this exists

The owner asked for ideas drawn from Aurral, a self-hosted music discovery app (its README, docs.aurral.org and its 3.0.0 release notes; its source was not read). Aurral's overall shape differs from Librarian's (it bundles its own library, downloaders, plugins and multi-user permissions), so none of that is proposed here. Four of its ideas fit Librarian as it is, and each extends something already in the code:

| Slice | Idea | Builds on |
|---|---|---|
| S1 | Say why a pick was made | `similar_to` in the personal payload |
| S2 | Richer feedback: block a genre, "More like this" | `recommendation_feedback.py`, `discovery_feedback` |
| S3 | Navidrome stars as a taste seed | seed weights for saves, `getAlbumList2` library reads |
| S4 | A Safer / Balanced / Deeper switch | `selection_policy.py`, lens popularity bands |

The order is the order of risk: S1 changes display only, S4 touches owner-approved lens definitions.

## 2. What the code does today (read 2026-11-15)

- **Reasons.** `build_personal_recommendation_payload` (`discovery/recommendation_payload.py`) writes a generic `reason` per category (for example "Genre tags connect this artist to your established musical interests."). The web UI hides that exact sentence and shows the artist bio instead (`static/app.js` around lines 1832, 2669 and 3232). The server also sets `similar_to` on every personal pick (`navidrome_server.py` lines 424, 476, 495, from `discovery/similar_artists.py`): the library artists the owner plays that share the most genre tags with the candidate, ties going to the artist played more. The web UI shows it as "Similar to: A, B" only when the category is `adjacent` (`app.js:1823`, `:2826`). Android shows it in `CoverStackDiscover.kt` and `FlowDiscover.kt`, but not in `DiscoverCard.kt`, which says the reason line is not shown. The macOS client decodes `similar_to` (`LibrarianClient.swift:12`) and its Cupertino Discover draws `reason`; I found no place where macOS draws `similar_to`. Lens picks carry their own reason ("From your current tastes: {tag}", `lens_week.py:98`); New releases and Deep Dive carry theirs.
- **Feedback.** Actions are save, dismiss, "Not this artist" (`dismiss_artist`) and remove-save (`navidrome_server.py:825-856`, `app/api/discovery.py:118`). Dismissals apply a decaying penalty (14-day half-life, 60-day expiry: 0.50 per album, 0.30 per artist, 0.10 per shared tag). Saves add a small boost (0.10) and seed tag selection with weight 1.0 (30-day half-life, 90-day expiry), all in `recommendation_feedback.py`. "Not this artist" hides the artist at read time (`discovery/list_payload.py`). Per-lens save and dismiss counts exist (`lens_feedback.py`, engine2 Phase 5). There is no genre-level block, no artist-level positive action and no screen that lists what is blocked.
- **Stars.** Navidrome reads for albums use `getAlbumList2` with `newest` and `alphabeticalByName` only (`navidrome_server.py`, `discovery/library_snapshot.py`). `intelligence/insights/runtime.py:56` reads an album's `starred` flag and Forgotten gems weights it, so stars reach Insights but not recommendations.
- **Adventurousness.** `discovery/selection_policy.py` has fixed category quotas and an adventurous floor of `count // 5`. The Deep cuts lens uses an owner-approved popularity band and never selects a candidate with an unknown audience figure (`discovery/lenses.py`). No setting changes any of this.

## 3. S1: Say why a pick was made

**Problem.** The reason is there for some picks and hidden or generic for others. `similar_to` is a tag overlap with the owner's library, not the signal that actually produced the pick, so for a ListenBrainz-based pick "Similar to" can name artists that played no part in it.

**Proposal.**
1. Server: add one optional field, `because`, to personal-pick payloads: `{kind, names}`, with kind one of `similar_artists`, `tag`, `lens`, `saved`. Existing fields keep their shape (no client breaks). Order of preference: the real seed when the candidate carries one, else `similar_to`, else the strongest shared tag, else absent. The text stays honest: tag-overlap names say "Shares genres with", a real seed says "Because you play".
2. Clients draw `because` for every category when present: web cards and rows, Android `DiscoverCard`, macOS Cupertino Discover. The generic category sentence is no longer needed as a fallback line.
3. The new text goes in `discovery/`, not `navidrome_server.py` (D-016).

**Open question to check before building.** Whether ListenBrainz collaborative-filtering candidates keep the seed recording or artist through `candidate_supply.py` and the allocator. If they do not, S1 starts with the tag and similar-artist forms only and a later slice carries the seed through.

**Acceptance.** A pick with a known seed shows it in all three clients; a pick with none shows the tag form or nothing, never invented names; fixtures cover each `kind`; old clients ignore the new field.

## 4. S2: Richer feedback

**Proposal.**
1. **Block genre.** A new feedback scope for genre (value stored by the existing `discovery_feedback` path, subject to a schema check). A blocked genre is excluded from the personal list, classics and lenses at selection time, using the same decay-free rule as "Not this artist" (a block stays until removed). It never hides or alters anything the owner already owns, and never changes library pages.
2. **More like this.** An artist-level positive action that writes the same kind of seed weight as a save (`saved_artist_seed_weights`, weight and decay from the existing constants). It boosts, never forces. It is separate from saving an album, so the owner can say "more of this artist" without keeping a specific album.
3. **Blocklist screen.** One page listing blocked genres and artists with an unblock control, on each client.
4. **"Less like this" (optional).** A soft artist demotion that does not hide, for the owner to choose against the current "Not this artist", which hides.

**Fits and limits.**
- D-027's skip and dismissal suppression memory is record-only and separate; this slice does not read it and does not change it.
- Per-lens feedback counts keep working; new actions record the originating lens in metadata as saves do today.
- Constants for the new actions are stated policy, as in `recommendation_feedback.py`, not fixture-calibrated claims.

**Acceptance.** Focused tests for a blocked genre removing candidates from each list, an owned album in that genre staying visible everywhere in the library, More like this raising seed weight with decay and expiry, unblocking restoring candidates, and an old client that never sends the new actions being unaffected.

## 5. S3: Navidrome stars as a seed

**Proposal.** Read the owner's starred artists and albums from Navidrome (the Subsonic `getStarred2` call, one request, no external provider) and add them as a seed source beside listening history and saves.
1. New read in `integrations/navidrome/`, cached with the library snapshot refresh, no new request per recommendation run.
2. New seed input in `discovery/` next to `profile_seeds.py`: a starred artist or album contributes its artist and tags with a weight and decay chosen by the owner, using the star date when the server gives one. Stars never make an owned album a candidate; they only steer what else is suggested.
3. A setting to switch the seed source on or off. Forgotten gems keeps reading stars as it does now, unchanged.

**Check before choosing weights.** Use the deterministic capture and replay tools (`recommendation/replay.py`, `profile_comparison.py`) to compare lists with and without stars on the owner's data, and report the overlap, as engine2 does for lenses. No quality claim without that run.

**Acceptance.** Focused tests for parsing the starred response (artists, albums, missing dates, empty library), the seed weight and decay, the on/off setting, and the stars input being ignored when Navidrome is unreachable.

## 6. S4: Safer / Balanced / Deeper

**Proposal.** One setting, `discovery_mode`, with values `safer`, `balanced` and `deeper`. **`balanced` is exactly today's behavior**, proven by a regression test that compares output with the setting absent and with `balanced`.
- Moves only existing knobs: the adventurous floor in `selection_policy.py`, and, if the owner agrees, the popularity band used by lists other than Deep cuts.
- The owner-approved lens definitions do not move unless the owner says so. The unknown-audience rule (an unknown audience is never called obscure) stays in every mode.
- The numbers for `safer` and `deeper` are not guessed here. They are set from a replay measurement of obscurity and genre spread (engine2 metrics), then approved by the owner.
- The setting lives in `settings/`, is shown in the web Settings and the Android and macOS clients, and changes the next refresh, not the list on screen.

**Acceptance.** `balanced` matches current output; `safer` and `deeper` change only the named knobs; a stored invalid value falls back to `balanced`; no lens definition changes without an explicit owner decision.

## 7. Slice plan

Each slice is its own PR, with focused tests only (the owner runs the full suite), and each server change goes in a new or existing `discovery/`, `integrations/` or `settings/` module, not `navidrome_server.py`.

| Slice | Content | Needs from the owner |
|---|---|---|
| S1a | Server `because` field with similar-artists and tag forms, tests | Approve the field and wording |
| S1b | Seed carried through candidates, if the open question says it is missing | Approve after S1a |
| S1c | Web, Android and macOS display | Approve after S1a |
| S2a | Genre-block scope, selection-time exclusion, tests | Approve; schema check |
| S2b | More like this (artist seed), tests | Approve; keep or drop "Less like this" |
| S2c | Blocklist screen and menu entries on the three clients | Approve after S2a, S2b |
| S3a | `getStarred2` read and parser, tests | Approve |
| S3b | Star seed input, setting, replay comparison | Approve weights after the replay |
| S4a | Setting, `balanced` regression test, knob wiring | Approve which lists the mode affects |
| S4b | `safer` and `deeper` values from a replay measurement | Approve the numbers |

Client slices that change screens need the owner's checks on a device and in a window; they are listed as checks, not claimed.

## 8. Decisions needed from the owner

1. Wording of the reason line, and whether tag-overlap names should be labelled as tag overlap. **Decided 2026-11-15 (owner):** tag-overlap names are labelled. `tag` reads "Because you listen to {tag}", `similar_artists` reads "Shares genres with {names}", a confirmed artist seed would read "Because you play {names}".
2. Whether a genre block hides picks only, or also lenses and classics (the proposal says both).
3. Whether to add "Less like this" next to "Not this artist".
4. Whether stars start switched on or off, and their weight against a save.
5. Which lists the discovery mode affects, and whether its popularity band may move the Deep cuts lens.

## 9. Not proposed

Multi-user permissions, share links, plugins, bundled downloaders, playlist imports and scheduled playlists. Playlist imports and scheduled playlists are the next candidates if the owner wants more from the same source; they are not part of this proposal.

## 10. Process

Documentation-only, committed directly to `main` by the owner's instruction. No code, tests or deployment. If approved, requirement entries (new `DISC-` rows) and decision entries are added with the slice that needs them.
