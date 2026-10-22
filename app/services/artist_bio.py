"""Pure artist-biography resolution from Wikidata and Wikipedia payloads."""

import re
from collections.abc import Iterable
from typing import Any


_ARTIST_DESCRIPTION_RE = re.compile(
    r"\b(?:band|musical group|rock group|pop group|music group|duo|orchestra|"
    r"choir|singer|singer-songwriter|musician|rapper|vocalist|songwriter|composer|"
    r"guitarist|bassist|drummer|keyboardist|record producer|music producer|"
    r"electronic musician|disc jockey|\bdj\b|folk musician|jazz musician|"
    r"instrumentalist|bandleader|conductor|arranger|saxophonist|pianist|trumpeter|"
    r"trombonist|clarinetist|flautist|flutist|violinist|cellist|violist|organist|"
    r"harpist|percussionist|vibraphonist|banjoist|lutenist|accordionist|"
    r"quartet|quintet|trio|ensemble|big band|vocal group)\b",
    re.IGNORECASE,
)


def resolve_artist_bio(name: str, entities: Iterable[dict[str, Any]], page: dict[str, Any]) -> str:
    """Use a Wikipedia extract only when its Wikidata identity is a music entity.

    If the page is missing, a disambiguation page, or points to a different
    entity, fall back to the best music-related Wikidata description.
    """
    key = str(name or "").casefold()
    music_entities = [
        item for item in entities
        if item.get("id")
        and _ARTIST_DESCRIPTION_RE.search(str(item.get("description") or ""))
    ]
    music_entities.sort(key=lambda item: (
        str(item.get("label") or "").casefold() != key,
        str(item.get("label") or "").casefold() != key.replace("the ", "", 1),
    ))

    bio = ""
    page_qid = str(page.get("wikibase_item") or "")
    if page_qid and page.get("type") != "disambiguation":
        matching_entity = next(
            (item for item in music_entities if str(item.get("id") or "") == page_qid),
            None,
        )
        if matching_entity:
            extract = " ".join(str(page.get("extract") or "").split())
            if extract:
                match = re.search(r"^.*?[.!?](?=\s|$)", extract)
                bio = match.group(0) if match else extract[:240]
                if len(bio) > 280:
                    bio = bio[:277].rsplit(" ", 1)[0] + "…"

    if not bio and music_entities:
        bio = str(music_entities[0].get("description") or "").strip()
    return bio
