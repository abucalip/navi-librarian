"""Star Operation S1a: the "because" field for personal picks.

``because`` says which profile artists made a pick come up: ``{"kind": "similar_artists",
"names": [...]}``. The names are artists you play that share at least one genre tag with the
candidate. That is tag overlap, not a confirmed seed, so clients must not say "because you
play" for it. The field is absent when there is no such artist.

Only ``similar_artists`` is emitted. A tag fallback would fire under exactly the same
condition (no profile artist shares a tag), so it is not built here. ``similar_to`` keeps its
existing value and shape.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from discovery.similar_artists import build_similar_to_lookup

BECAUSE_SIMILAR_ARTISTS = "similar_artists"


def build_because(similar_names: Iterable[str]) -> dict[str, Any] | None:
    """The ``because`` value for a pick's similar-artist names, or None when there are none."""
    names = [str(name) for name in similar_names if name]
    if not names:
        return None
    return {"kind": BECAUSE_SIMILAR_ARTISTS, "names": names}


def build_pick_context_lookup(
    listens: Iterable[Mapping[str, Any]],
    genre_cache: Mapping[str, Iterable[str]],
    music_key: Callable[[Any], str],
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Prepare a per-run lookup returning the fields a personal pick adds to its payload.

    The result always has ``similar_to`` (unchanged from ``build_similar_to_lookup``) and has
    ``because`` only when ``similar_to`` is not empty.
    """
    similar_to = build_similar_to_lookup(listens, genre_cache, music_key)

    def pick_context(candidate: Mapping[str, Any]) -> dict[str, Any]:
        names = similar_to(candidate)
        context: dict[str, Any] = {"similar_to": names}
        because = build_because(names)
        if because is not None:
            context["because"] = because
        return context

    return pick_context
