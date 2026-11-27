"""Structured LB Radio seeds and full-list ownership presentation (LB-18)."""

from dataclasses import asdict
import unicodedata

from discovery.recording_match import match_recordings


def radio_seed(artist_mbid, tag):
    """Accept one seed and prevent tag text from introducing prompt operators."""
    if (artist_mbid is None) == (tag is None):
        raise ValueError("Provide exactly one artist_mbid or tag.")
    if artist_mbid is not None:
        value = str(artist_mbid)
        return {"kind": "artist", "value": value}, f"artist:({value})"
    if any(unicodedata.category(char).startswith("C") for char in tag):
        raise ValueError("Tag contains unsupported characters.")
    value = " ".join(unicodedata.normalize("NFC", tag).casefold().split())
    if not value or len(value) > 80 or not all(char.isalnum() or char in " -_&'/+." for char in value):
        raise ValueError("Tag must be 1–80 characters without prompt operators.")
    return {"kind": "tag", "value": value}, f"tag:({value})"


def mix_tracks(playlist, owned):
    """Keep source order and repeats, including missing and ambiguous recordings."""
    matches = match_recordings(playlist.tracks, owned) if owned is not None else None
    rows = []
    for position, track in enumerate(playlist.tracks):
        match = matches[position] if matches is not None else None
        rows.append({**asdict(track), "match_state": match.state if match else None,
                     "song_id": match.song_id if match else None})
    return {"total_count": len(rows),
            "owned_count": sum(row["match_state"] == "owned" for row in rows) if matches is not None else None,
            "tracks": rows}
