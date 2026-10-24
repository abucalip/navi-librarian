"""Deep cuts candidate supply: tiered tag radio with a MusicBrainz tag-search tail.

Owner-approved definition (docs/engine2.md, lens catalog): the ListenBrainz tag radio at the
50-75% popularity band comes first, then the 75-100% band, then the MusicBrainz tag search.
Each later tier runs only for the queries the earlier tiers left without an album.

Unwired: nothing in the recommendation path calls this yet (Phase 4 wiring is a separate
decision). The caller supplies the queries, providers and shared lane state, as for the
other tag lanes.
"""
from datetime import date
from typing import Any

# (pop_begin, pop_end) per radio tier, in order. Low percent is the most popular recordings.
DEEP_CUTS_RADIO_BANDS = ((50, 75), (75, 100))
# Albums kept per seed tag from the radio, which returns 20 recordings per call. Measured
# 2026-10-24: 10 filled the lenses best; 15 exceeds the 60 candidates the selection checks.
DEEP_CUTS_ALBUMS_PER_QUERY = 10


def run_deep_cuts_tag_supply(
    queries, *, providers, headers, albums, failures, state, lens: str, day: str,
) -> list[tuple[int, Any]]:
    """Add Deep cuts candidates from the tiers in order. Returns one (added, error_class)
    pair per query, aligned with ``queries``, from the tier that last attempted it. A query
    no tier reached (the lane cap or an unavailable provider stopped it) is
    ``(0, "not_attempted")``.

    Radio answers are keyed by ``lens`` and ``day`` (ISO date): one fixed sample per tag
    for the day, a fresh draw on the next day, and a separate draw for each lens.

    The tag radio needs ``providers.http_post``; without it the radio tiers are skipped
    and the MusicBrainz tail runs for every query. ``state["unavailable"]`` set by a radio
    tier stops the later radio tiers but not the MusicBrainz tail, which is a different
    provider.
    """
    from discovery.candidate_gathering import _run_tag_queries, run_radio_lane

    if not lens or not isinstance(lens, str):
        raise ValueError("lens must be a non-empty string")
    date.fromisoformat(day)  # raises ValueError unless an ISO date
    scope = f"{lens}:{day}"
    outcomes: list[tuple[int, Any]] = [(0, "not_attempted")] * len(queries)
    remaining = list(range(len(queries)))
    if providers.http_post is not None:
        for pop_begin, pop_end in DEEP_CUTS_RADIO_BANDS:
            if not remaining:
                break
            tier = run_radio_lane(
                [queries[i] for i in remaining], providers=providers, albums=albums,
                failures=failures, state=state, pop_begin=pop_begin, pop_end=pop_end,
                scope=scope, per_query=DEEP_CUTS_ALBUMS_PER_QUERY,
            )
            for index, outcome in zip(remaining, tier):
                outcomes[index] = outcome
            remaining = [index for index, (added, _error) in zip(remaining, tier) if added == 0]
            if state["unavailable"]:
                # A retryable radio failure: no further radio tiers, but the tail below
                # still runs for what is left, since it is a different provider.
                break

    if remaining:
        state["unavailable"] = False
        with providers.http_client(timeout=20, follow_redirects=True) as client:
            tail = _run_tag_queries(
                [queries[i] for i in remaining], providers=providers, client=client,
                headers=headers, albums=albums, failures=failures, state=state,
            )
        for index, outcome in zip(remaining, tail):
            outcomes[index] = outcome
    return outcomes
