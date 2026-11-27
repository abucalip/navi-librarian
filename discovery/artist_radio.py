"""Owned-first Artist Radio selection. Pure: providers only influence ranking."""

from collections import Counter, deque
from dataclasses import replace
import math

from discovery.recording_match import match_recordings
from discovery.search.normalize import normalize_key, normalize_mbid
from integrations.listenbrainz.jspf import PlaylistTrack

MAX_SIMILAR_ARTISTS = 5
# Seed share, local-play weight, popularity weight. Input signals are bounded to [0, 1].
MODES = {"familiar": (0.60, 0.65, 0.35), "explore": (0.35, -0.35, 0.65),
         "deep_cuts": (0.20, -0.70, -0.30)}


def radio_artists(owned, seed_mbid, records):
    """Resolve only unique artist identities; conflicting known MBIDs never fall back to names."""
    seeds = [a for a in owned.artists if normalize_mbid(a.get("mbid")) == seed_mbid]
    if len(seeds) != 1:
        return []
    selected = [seeds[0]]
    for record in records:
        mbid = normalize_mbid(record.get("mbid"))
        matches = [a for a in owned.artists if mbid and normalize_mbid(a.get("mbid")) == mbid]
        if not matches:
            matches = [a for a in owned.artists
                       if normalize_key(a["name"]) == normalize_key(record.get("name"))]
            if len(matches) == 1 and mbid and normalize_mbid(matches[0].get("mbid")):
                matches = []
        if len(matches) == 1 and matches[0]["id"] not in {a["id"] for a in selected}:
            selected.append({**matches[0], "mbid": matches[0].get("mbid") or mbid})
        if len(selected) == MAX_SIMILAR_ARTISTS + 1:
            break
    return selected


def _popularity(owned, artists, rankings):
    tracks, scores = [], []
    for artist in artists:
        rows = rankings.get(artist["id"], [])
        for position, row in enumerate(rows):
            tracks.append(PlaylistTrack(
                len(tracks), row.get("recording_mbid"), row.get("title"),
                row.get("artist") or artist["name"], row.get("album"), row.get("duration_ms"),
            ))
            scores.append(1 - position / max(1, len(rows)))
    # Scope matching to eligible artists before invoking the shared conservative matcher.
    ids = {a["id"] for a in artists}
    scoped = replace(owned, songs=tuple(s for s in owned.songs if s["artist_id"] in ids))
    found = {}
    for match, score in zip(match_recordings(tracks, scoped), scores):
        if match.song_id:
            found[match.song_id] = max(score, found.get(match.song_id, 0))
    return found


def _take_rounds(buckets, limit):
    result = []
    while len(result) < limit and any(buckets):
        for bucket in buckets:
            if bucket and len(result) < limit:
                result.append(bucket.popleft())
    return result


def build_queue(owned, artists, rankings, *, familiarity="familiar", count=40):
    """Rank library candidates, balance artists and deduplicate exact recording copies."""
    if not artists:
        return []
    share, play_weight, popular_weight = MODES[familiarity]
    popularity = _popularity(owned, artists, rankings)
    ids = {a["id"] for a in artists}
    songs = [s for s in owned.songs if s["artist_id"] in ids and s.get("id")]
    maximum = max((s.get("plays", 0) for s in songs), default=0)

    def score(song):
        plays = math.log1p(song.get("plays", 0)) / math.log1p(maximum) if maximum else 0
        return play_weight * plays + popular_weight * popularity.get(song["id"], 0)

    buckets = {a["id"]: deque() for a in artists}
    seen = set()
    for song in sorted(songs, key=lambda s: s["id"]):
        # Without a recording ID, keep separate library versions intact.
        identity = normalize_mbid(song.get("recording_mbid")) or (song["id"],)
        if identity in seen:
            continue
        seen.add(identity)
        buckets[song["artist_id"]].append(song)
    for artist_id, bucket in buckets.items():
        buckets[artist_id] = deque(sorted(bucket, key=lambda s: (-score(s), s["id"])))
    seed = buckets[artists[0]["id"]]
    selected = _take_rounds([seed], round(count * share))
    similar = [buckets[a["id"]] for a in artists[1:]]
    selected += _take_rounds(similar, count - len(selected))
    selected += _take_rounds(list(buckets.values()), count - len(selected))

    # Interleave each artist's selected songs in proportion to its final allocation.
    totals = Counter(s["artist_id"] for s in selected)
    chosen = {a["id"]: deque(s for s in selected if s["artist_id"] == a["id"]) for a in artists}
    served = Counter()
    result = []
    while any(chosen.values()):
        artist_id = min((a for a in chosen if chosen[a]), key=lambda a: served[a] / totals[a])
        song = chosen[artist_id].popleft()
        served[artist_id] += 1
        result.append({"song_id": song["id"], "title": song["name"], "artist": song["artist"],
                       "artist_id": artist_id, "album": song.get("album"),
                       "album_id": song.get("album_id"), "duration": song.get("duration"),
                       "recording_mbid": song.get("recording_mbid"), "owned": True})
    return result
