"""One-line facts about the song that is playing, its album and its artist, for the Mac player bar.

Read from the store only (no provider call, no write), built on the :class:`KnowledgeReader` walk like the other
knowledge pages. Every line is something MusicBrainz states, worded as a statement with its source, and a line
appears only when the store holds the facts behind it: an absent fact is never turned into a claim about the world.
Nothing is ranked or guessed ("notable", "famous", "first ever" are never written).

A fact is ``{kind, scope, text, source, source_url, link}``. ``scope`` is ``song``, ``album`` or ``artist``; ``link``
is ``{type, mbid}`` of the page that backs the line, or null. Lines are stable in order (song, album, artist) so a
client can rotate through them.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import REL_APPEARS_ON
from ..graph import Limits
from ..store import repositories as repo
from .pages import PERSON_TYPES, _album_for, _coverage, _life_span

MAX_NAMES = 3
WALK_ROWS = 200
SOURCE = "MusicBrainz"

# Substring of the relation or role, in the order the lines are shown.
_CREDIT_LINES = (
    ("producer", "Produced by"),
    ("engineer", "Engineered by"),
    ("mix", "Mixed by"),
    ("mastering", "Mastered by"),
    ("arranger", "Arranged by"),
)
_YEAR_ONLY = 4


def song_facts_page(reader, recording: dict[str, Any], *, album: dict[str, Any] | None = None,
                    artist: dict[str, Any] | None = None, limit: int = 200) -> dict[str, Any]:
    """Facts for a recording, plus its album (release or release group) and artist when given."""
    if recording["type"] != "recording":
        raise ValueError("song facts need a recording entity")
    if album is not None and album["type"] not in ("release", "release_group"):
        raise ValueError("the album must be a release or a release group")
    if artist is not None and artist["type"] not in PERSON_TYPES:
        raise ValueError("the artist must be an artist, person or group")
    db = reader._db
    facts: list[dict[str, Any]] = []
    facts += _song_facts(reader, db, recording, limit)
    if album is not None:
        facts += _album_facts(reader, album, limit)
    if artist is not None:
        facts += _artist_facts(reader, db, artist, limit)
    status = reader.slice_status()
    return {
        "recording": {k: recording.get(k) for k in ("id", "type", "mbid", "canonical_name", "owned")},
        "facts": facts,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(facts)),
                                         "dump_timestamp": status["dump_timestamp"]}},
    }


# ---------------------------------------------------------------- song
def _song_facts(reader, db, recording: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    walk = reader.connections(recording["id"], credits_only=True,
                              limits=Limits(max_depth=1, max_rows=min(limit, WALK_ROWS), page_size=min(limit, WALK_ROWS)))
    people: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    places: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    samples, sampled_by, remixes, remixed_as = [], [], [], []
    works: list[dict[str, Any]] = []
    for hop in walk["hops"]:
        other, evidence = hop["entity"], hop["evidence"]
        kind = other["type"]
        if kind in PERSON_TYPES:
            people.append((other, evidence))
        elif kind in ("place", "event"):
            places.append((other, evidence))
        elif kind == "work":
            works.append(other)
        elif kind == "recording":
            for ev in evidence:
                rel = (ev["relation"] or "").lower()
                # MusicBrainz states the sampling recording as the first end of "samples material".
                if "sampl" in rel:
                    (samples if ev["direction"] == "out" else sampled_by).append(other)
                elif "remix" in rel:
                    (remixes if ev["direction"] == "out" else remixed_as).append(other)
    out: list[dict[str, Any]] = []

    for other, evidence in places[:2]:
        verb = _place_verb(evidence)
        year = next((ev["valid_from"][:_YEAR_ONLY] for ev in evidence if ev["valid_from"]), None)
        where = f"{verb} {other['canonical_name']}" + (f" in {year}" if year else "")
        out.append(_fact("recorded_at", "song", where, evidence, other))

    for needle, phrase in _CREDIT_LINES:
        names = _names_for(people, needle)
        if names:
            out.append(_fact(needle, "song", f"{phrase} {_join(names)}", _evidence_for(people, needle), _first_for(people, needle)))

    players = _players(people)
    if players:
        out.append(_fact("players", "song", "Played by " + _join(players), [], None))

    for work in works[:1]:
        out += _work_facts(reader, db, work, recording)

    if samples:
        out.append(_fact("samples", "song", f"Samples “{samples[0]['canonical_name']}”" + _and_more(len(samples)), [], samples[0]))
    if sampled_by:
        text = f"Sampled in “{sampled_by[0]['canonical_name']}”" if len(sampled_by) == 1 \
            else f"Sampled in {len(sampled_by)} other recordings, among them “{sampled_by[0]['canonical_name']}”"
        out.append(_fact("sampled_by", "song", text, [], sampled_by[0]))
    if remixes:
        out.append(_fact("remix_of", "song", f"A remix of “{remixes[0]['canonical_name']}”", [], remixes[0]))
    if remixed_as:
        out.append(_fact("remixed_as", "song", f"Remixed as “{remixed_as[0]['canonical_name']}”" + _and_more(len(remixed_as)), [], remixed_as[0]))

    out += _release_facts(db, recording)
    return out


def _work_facts(reader, db, work: dict[str, Any], recording: dict[str, Any]) -> list[dict[str, Any]]:
    page = reader.work_page(id=work["id"], limit=WALK_ROWS)
    if page is None:
        return []
    out: list[dict[str, Any]] = []
    writers = [w["entity"]["canonical_name"] for w in page["written_by"] if w["entity"]["canonical_name"]]
    if writers:
        out.append(_fact("written_by", "song", f"Written by {_join(writers[:MAX_NAMES], len(writers))}", [], work))
    others = max(0, page["summary"]["recordings"] - 1)
    covers = page["summary"]["covers"]
    if covers:
        out.append(_fact("covers", "song", f"MusicBrainz lists {covers} cover{'s' if covers != 1 else ''} of this composition", [], work))
    elif others:
        out.append(_fact("other_recordings", "song", f"MusicBrainz lists {others} other recording{'s' if others != 1 else ''} of this composition", [], work))
    return out


def _release_facts(db, recording: dict[str, Any]) -> list[dict[str, Any]]:
    """Where the recording was released: how many albums, and the earliest stated date."""
    albums: dict[int, dict[str, Any]] = {}
    dates: list[str] = []
    for edge in repo.edges_from(db, recording["id"], REL_APPEARS_ON):
        release = repo.get_entity(db, edge["to_id"])
        if release is None:
            continue
        albums.setdefault(_album_for(db, release)["id"], _album_for(db, release))
        row = db.execute("SELECT date FROM release_facts WHERE entity_id = ?", (release["id"],)).fetchone()
        if row and row["date"]:
            dates.append(row["date"])
    out: list[dict[str, Any]] = []
    if len(albums) > 1:
        out.append(_fact("appears_on", "song", f"Appears on {len(albums)} albums or releases in MusicBrainz", [], None))
    if dates:
        out.append(_fact("first_release", "song", f"Earliest release date on record: {_pretty_date(min(dates))}", [], None))
    return out


# ---------------------------------------------------------------- album
def _album_facts(reader, album: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    page = reader.album_dossier(id=album["id"], type=album["type"], limit=min(limit, 100))
    if page is None:
        return []
    out: list[dict[str, Any]] = []
    editions = page["release_family"]["editions"]
    dated = sorted(e["date"] for e in editions if e.get("date"))
    if len(editions) > 1:
        tail = f", the earliest from {_pretty_date(dated[0])}" if dated else ""
        out.append(_fact("editions", "album", f"{len(editions)} editions of this album in MusicBrainz{tail}", [], album))
    elif dated:
        out.append(_fact("album_date", "album", f"Released {_pretty_date(dated[0])}", [], album))
    labels = [l["entity"]["canonical_name"] for l in page["labels"] if l["entity"]["canonical_name"]]
    if labels:
        out.append(_fact("label", "album", f"Released on {_join(labels[:2], len(labels))}", [], album))
    producers = [p["entity"]["canonical_name"] for p in page["people"]
                 if any("producer" in ((c["relation"] or "") + " " + (c["role"] or "")).lower() for c in p["credits"])]
    if producers:
        out.append(_fact("album_producer", "album", f"Album produced by {_join(producers[:MAX_NAMES], len(producers))}", [], album))
    runtime = [t for t in page["tracks"] if t.get("position")]
    if runtime:
        out.append(_fact("track_count", "album", f"{len(runtime)} tracks on the release MusicBrainz lists", [], album))
    return out


# ---------------------------------------------------------------- artist
def _artist_facts(reader, db, artist: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    span = _life_span(db, artist["id"])
    row = db.execute("SELECT kind FROM artist_facts WHERE entity_id = ?", (artist["id"],)).fetchone()
    kind = (row["kind"] if row else None) or ("Group" if artist["type"] == "group" else "Person" if artist["type"] == "person" else None)
    if span and span["begin"]:
        began = _pretty_date(span["begin"])
        ended = _pretty_date(span["end"]) if span["ended"] and span["end"] else None
        if kind == "Person":
            text = f"Born {began}" if not span["ended"] else f"Lived {began}" + (f" to {ended}" if ended else "")
        else:  # a group, or an artist MusicBrainz does not type: "together" would be a guess for the latter
            lead = "Together" if kind in ("Group", "Orchestra", "Choir") else "Active"
            text = f"{lead} since {began}" if not span["ended"] else f"{lead} from {began}" + (f" until {ended}" if ended else "")
        out.append(_fact("life_span", "artist", text, [], artist))
    walk = reader.connections(artist["id"], credits_only=True,
                              limits=Limits(max_depth=1, max_rows=min(limit, WALK_ROWS), page_size=min(limit, WALK_ROWS)))
    members = []
    for hop in walk["hops"]:
        other = hop["entity"]
        if other["type"] in PERSON_TYPES and any("member" in (ev["relation"] or "").lower() for ev in hop["evidence"]):
            members.append(other["canonical_name"])
    members = [m for m in members if m]
    if members:
        out.append(_fact("members", "artist", f"Linked members: {_join(members[:4], len(members))}", [], artist))
    return out


# ---------------------------------------------------------------- helpers
def _fact(kind: str, scope: str, text: str, evidence: list[dict[str, Any]], link: dict[str, Any] | None) -> dict[str, Any]:
    source_url = next((e["source_url"] for e in evidence if e.get("source_url")), None)
    return {"kind": kind, "scope": scope, "text": text, "source": SOURCE, "source_url": source_url,
            "link": {"type": link["type"], "mbid": link["mbid"]} if link and link.get("mbid") else None}


def _join(names: list[str], total: int | None = None) -> str:
    names = list(names)
    extra = (total or len(names)) - len(names)
    if extra > 0:
        return ", ".join(names) + f" and {extra} more"
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _and_more(count: int) -> str:
    return f" and {count - 1} other recording{'s' if count > 2 else ''}" if count > 1 else ""


def _blob(ev: dict[str, Any]) -> str:
    return f"{ev['relation'] or ''} {ev['role'] or ''}".lower()


def _names_for(people, needle: str) -> list[str]:
    names = [p["canonical_name"] for p, evs in people if any(needle in _blob(e) for e in evs) and p["canonical_name"]]
    return list(dict.fromkeys(names))[:MAX_NAMES]


def _evidence_for(people, needle: str) -> list[dict[str, Any]]:
    return [e for _, evs in people for e in evs if needle in _blob(e)]


def _first_for(people, needle: str) -> dict[str, Any] | None:
    return next((p for p, evs in people if any(needle in _blob(e) for e in evs)), None)


def _players(people) -> list[str]:
    """People credited with an instrument or voice, as "Name (instrument)" for the first few."""
    out = []
    for person, evs in people:
        parts = sorted({(e["role"] or "").strip() for e in evs
                        if ("instrument" in (e["relation"] or "").lower() or "vocal" in (e["relation"] or "").lower()) and e["role"]})
        if parts and person["canonical_name"]:
            out.append(f"{person['canonical_name']} ({', '.join(parts)})")
    return out[:MAX_NAMES]


def _place_verb(evidence: list[dict[str, Any]]) -> str:
    blob = " ".join(_blob(e) for e in evidence)
    if "master" in blob:
        return "Mastered at"
    if "mix" in blob:
        return "Mixed at"
    if "produc" in blob:
        return "Produced at"
    return "Recorded at"


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _pretty_date(value: str) -> str:
    """``1986``, ``1986-03`` or ``1986-03-17`` as "1986", "March 1986" or "17 March 1986"."""
    parts = (value or "").split("-")
    try:
        year = int(parts[0])
        if len(parts) == 1:
            return str(year)
        month = _MONTHS[int(parts[1]) - 1]
        return f"{month} {year}" if len(parts) == 2 else f"{int(parts[2])} {month} {year}"
    except (ValueError, IndexError):
        return value
