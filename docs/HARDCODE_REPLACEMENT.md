# Plan: replace hard-coded taste with derived behavior

Status: complete. Derived is the only mode; the fixed core/exploration sets, artist-name lists, adventurous tags and the mode switch are removed (PRs #561-#571). The tag-to-family grouping rules remain as vocabulary. Evidence: `PROJECT_LOG.md`. The inventory and line references below describe the original state.

## Problem

The recommendation engine assumes one listener's taste. A fixed vocabulary of genre families (jazz, hip-hop, alternative, rock, Brazilian, R&B/soul, electronic, funk, African, North African/Middle Eastern) and a list of named artists decide what counts as "close", "cross-genre", and "adventurous". For a listener whose tags fall outside that vocabulary (metal, K-pop, classical, and so on), `genre_families()` returns nothing, almost every candidate is classed "adventurous", and the exploration bonus still goes to African and North African music.

## Inventory of hard-coded taste

| # | Location | Role |
|---|---|---|
| 1 | `discovery/recommendations.py` `genre_families()` | Tag to family map used for category, exploration bonus, and query labels |
| 2 | `discovery/candidate_gathering.py` `core_families` / `exploration_families` (~line 1185) | Fixed definition of "interests" |
| 3 | `recent_style_families()`, `primary_recent_family()`, `deep_dive_genre_families()`, and `deepDiveGenre()` / `genreRowLabel()` in `static/app.js` | Four more copies of the family vocabulary with slightly different keywords, plus display labels |
| 4 | `_REGIONAL_RECOMMENDATION_ARTIST_FAMILIES` and the name sets in `classify_diversity_style()` | About 20 named artists, used only when a candidate has no tags |
| 5 | `_ADVENTUROUS_RECOMMENDATION_TAGS` | Fixed tag list that forces the "adventurous" category |

Consumers: `classify_recommendation_category`, `apply_familiarity_exploration_bonus` (x1.10 for exploration families), the `family_cap=1` diversity rule, `discovery/tag_queries.py` query labels, and the Deep Dives rows.

Already dynamic and to be kept: tag-query selection weighted by decayed listening, and recent family counts from the rolling 30-day scrobbles. `diversity_style_targets` is already empty, so `classify_diversity_style()` mostly affects diagnostics.

## Principles

- No behavior change for the owner until a derived mode is explicitly enabled.
- Provider tags drive classification; artist-name lists are removed, not extended.
- Any ranking change needs replay evidence and owner approval (see `ACTIVE_WORK.md` section 3 and `DEVELOPMENT_WORKFLOW.md`).
- Keep family/similarity logic server-side; the UI only displays what the server sends.

## Phases

### Phase 1: consolidate (no behavior change)

- Create one module (for example `discovery/taste_families.py`) holding the family rules, the keyword tables, and display labels.
- Make `genre_families`, `recent_style_families`, `primary_recent_family`, and `deep_dive_genre_families` read from it.
- Send family labels from the server so `app.js` stops carrying its own copy.
- Existing tests must pass unchanged. Where the four tables differ today, keep each difference as an explicit named profile in the module rather than silently merging them, and record the differences in `PROJECT_LOG.md`.

### Phase 2: externalize the defaults

- Move the current tables, the core/exploration sets, the artist fallback list, and the adventurous tags into a settings file under `settings/`, loaded once.
- The shipped default reproduces today's output exactly.
- Verify with `recommendation/replay.py` and `profile_comparison.py` that outputs are identical.

### Phase 3: derived profile mode (behind a setting, off by default)

- Compute `core_families` from decayed listen weight: the tags covering about 80% of the profile weight.
- Compute `exploration_families` as tags that are well represented in the similar-artist and collaborative-filtering candidate pool but below the core threshold.
- Use normalized tags as family keys when no rule matches, so unfamiliar genres get a family instead of "other". Consider MusicBrainz genre ancestry (for example hard bop to jazz) for grouping.
- Replace the fixed x1.10 target with the derived exploration set.
- Replace the artist-name fallback with the anchor or similar-artist tags already used in `discovery/deep_dive_candidates.py`.
- Define "adventurous" relative to the profile: low weighted overlap with the user's tags, or tags rare in their library, instead of the fixed list.

### Phase 4: evaluate and decide

- Replay several different profiles (the owner's, plus synthetic or captured profiles such as metal-only, classical-only, mixed) in fixed and derived modes.
- Compare category mix, family spread, empty/"unclassified" rates, and diversity.
- Present evidence to the owner; only then propose making the derived mode the default and removing the fixed tables.

## Acceptance criteria

- Phase 1 and 2: full unit suite and required CI pass; replay output is identical to before.
- Phase 3: for a non-jazz profile, fewer than half of candidates land in "adventurous" purely because of a vocabulary miss; the exploration bonus no longer depends on African or North African tags.
- No named artist or genre list remains in classification code once Phase 4 is approved.
- Test plan: update the tests that pin the current vocabulary (`tests/test_discovery_recommendations.py`, `tests/test_discovery_tag_queries.py`, `tests/test_discovery_classics_ratings.py`), and add tests with at least two non-jazz profiles.

## Risks and open questions for the owner

- The four existing tables differ; deciding which behavior is canonical is an owner decision.
- Derived profiles change ranking, so Phase 3 and later need owner approval and replay evidence.
- Sparse listening history makes the derived profile noisy; a minimum-history fallback to the defaults is needed.
- Live provider capture is not needed for Phases 1-2; Phase 4 may need captured profiles, which require owner approval if they involve live requests.
