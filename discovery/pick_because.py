"""Star Operation S1a: the "because" field for personal picks.

``because`` says which profile artists made a pick come up: ``{"kind": "similar_artists",
"names": [...]}``. The names are artists you play that share at least one genre tag with the
candidate. That is tag overlap, not a confirmed seed, so clients must not say "because you
play" for it. The field is absent when there is no such artist.

Star Operation S1b adds the ``tag`` kind, which is a real seed: a candidate that a profile
tag search surfaced carries ``seed_tags`` (the tags from the owner's own listening that the
search used), and ``because`` is ``{"kind": "tag", "names": [tag, ...]}``. It wins over
``similar_artists`` because it is the reason the candidate was gathered. ListenBrainz
collaborative-filtering candidates carry no seed (the endpoint returns only recording MBIDs
and a score), so they keep the ``similar_artists`` form. ``similar_to`` keeps its existing
value and shape.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from discovery.similar_artists import build_similar_to_lookup

BECAUSE_SIMILAR_ARTISTS = "similar_artists"
BECAUSE_TAG = "tag"
PROFILE_STYLE_PREFIX = "profile:"
MAX_SEED_TAGS = 3


def record_seed_tag(candidate: dict[str, Any], style: str, tag: str | None) -> None:
    """Remember on ``candidate`` the profile tag whose search surfaced it.

    Only profile-derived searches count: an exploration tag comes from the candidate pool, not
    from the owner's listening, so it is not a reason to show. Duplicate tags are ignored.
    """
    if not tag or not str(style).startswith(PROFILE_STYLE_PREFIX):
        return
    tags = candidate.setdefault("seed_tags", [])
    if tag not in tags:
        tags.append(tag)


def build_because(similar_names: Iterable[str]) -> dict[str, Any] | None:
    """The ``because`` value for a pick's similar-artist names, or None when there are none."""
    names = [str(name) for name in similar_names if name]
    if not names:
        return None
    return {"kind": BECAUSE_SIMILAR_ARTISTS, "names": names}


def build_seed_because(seed_tags: Iterable[str] | None) -> dict[str, Any] | None:
    """The ``because`` value for a candidate's seed tags, or None when it has none."""
    tags = [str(tag) for tag in (seed_tags or ()) if tag][:MAX_SEED_TAGS]
    if not tags:
        return None
    return {"kind": BECAUSE_TAG, "names": tags}


def build_pick_context_lookup(
    listens: Iterable[Mapping[str, Any]],
    genre_cache: Mapping[str, Iterable[str]],
    music_key: Callable[[Any], str],
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Prepare a per-run lookup returning the fields a personal pick adds to its payload.

    The result always has ``similar_to`` (unchanged from ``build_similar_to_lookup``). It has
    ``because`` of kind ``tag`` when the candidate carries a seed tag, else of kind
    ``similar_artists`` when ``similar_to`` is not empty, else no ``because``.
    """
    similar_to = build_similar_to_lookup(listens, genre_cache, music_key)

    def pick_context(candidate: Mapping[str, Any]) -> dict[str, Any]:
        names = similar_to(candidate)
        context: dict[str, Any] = {"similar_to": names}
        because = build_seed_because(candidate.get("seed_tags")) or build_because(names)
        if because is not None:
            context["because"] = because
        return context

    return pick_context
