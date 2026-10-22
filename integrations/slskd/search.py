"""Pure query, response, and candidate helpers for slskd search."""

import math
import re
from collections import defaultdict
from pathlib import Path

def expected_track_count(metadata):
    """Read an expected track count from common recommendation metadata shapes."""
    if not isinstance(metadata, dict):
        return None
    keys = ("track_count", "trackCount", "number_of_tracks", "numberOfTracks",
            "total_tracks", "totalTracks", "tracks_count", "tracksCount", "trackcount")
    queue = [metadata]
    seen = set()
    while queue:
        current = queue.pop(0)
        if not isinstance(current, dict) or id(current) in seen:
            continue
        seen.add(id(current))
        for key in keys:
            value = current.get(key)
            try:
                count = int(value)
                if count > 0:
                    return count
            except (TypeError, ValueError):
                pass
        for key in ("tracks", "tracklist", "track_list", "album", "release", "metadata"):
            value = current.get(key)
            if isinstance(value, list) and value:
                # Track objects are strong evidence; avoid mistaking unrelated arrays for tracks.
                if all(isinstance(item, dict) for item in value):
                    return len(value)
            elif isinstance(value, dict):
                queue.append(value)
    return None

def track_identity(filename, music_key):
    """A filename-based track identity that ignores extensions and numeric collision suffixes."""
    import re
    name = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem = Path(name).stem.casefold()
    stem = re.sub(r"_\d+$", "", stem)
    return music_key(stem)


def album_path_match(album, text):
    """Match album names in remote paths despite punctuation and edition suffixes."""
    import math
    import re
    album_text = str(album or "").strip()
    path_text = str(text or "").strip()
    if not album_text or not path_text:
        return False
    tokens = re.findall(r"[a-z0-9]+", album_text.casefold())
    path_tokens_list = re.findall(r"[a-z0-9]+", path_text.casefold())
    if tokens and any(
        path_tokens_list[index:index + len(tokens)] == tokens
        for index in range(len(path_tokens_list) - len(tokens) + 1)
    ):
        return True
    stopwords = {"a", "an", "and", "of", "the", "to", "in", "on", "for"}
    meaningful = [token for token in tokens if token not in stopwords] or tokens
    if not meaningful:
        return False
    unique_tokens = set(meaningful)
    path_tokens = set(path_tokens_list)
    overlap = sum(1 for token in unique_tokens if token in path_tokens)
    if len(unique_tokens) == 1:
        return overlap == 1
    return overlap >= max(2, math.ceil(len(unique_tokens) * 0.6))


def _mask_word(word):
    """Replace the first alphanumeric character of a word with a Soulseek wildcard."""
    for index, char in enumerate(word):
        if char.isalnum():
            return word[:index] + "*" + word[index + 1:]
    return word


def masked_artist_variants(artist):
    """Return wildcard-masked artist names for terms the network blocks outright.

    First the first word only ("*orillaz"), then every word ("*ink *loyd").
    Words under three characters are left intact to keep queries selective.
    """
    words = artist.split()
    if not words:
        return []
    first_only = [
        _mask_word(word) if index == 0 and len(word) >= 3 else word
        for index, word in enumerate(words)
    ]
    every_word = [_mask_word(word) if len(word) >= 3 else word for word in words]
    return [" ".join(first_only), " ".join(every_word)]


def search_queries(artist, album):
    """Return a small, ordered set of progressively broader Soulseek queries."""
    import re

    artist = re.sub(r"\s+", " ", str(artist or "")).strip()
    album = re.sub(r"\s+", " ", str(album or "")).strip()
    if not artist or not album:
        return []

    punctuation_normalized = re.sub(r"[^\w\s]", " ", album)
    primary_title = re.sub(r"\s*\([^)]*\)", " ", album)
    variants = [
        f"{artist} {album}",
        *(f"{masked} {album}" for masked in masked_artist_variants(artist)),
        f"{artist} {punctuation_normalized}",
        f"{artist} {primary_title}",
    ]
    queries = []
    seen = set()
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()
        key = query.casefold()
        if query and key not in seen:
            queries.append(query)
            seen.add(key)
    return queries


def response_items(payload):
    """Normalize slskd search results across list and wrapped API payloads."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("responses")
        if not isinstance(items, list):
            items = payload.get("items")
    else:
        items = []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def path_match_diagnostics(payload, artist, album, limit=10, *, music_key, album_path_match):
    """Return bounded evidence explaining why visible audio paths did not match."""
    import re
    audio_exts = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape"}
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit = 10
    samples = []
    for response in payload if isinstance(payload, list) else []:
        username = response.get("username") or response.get("user") or ""
        files = response.get("files") or response.get("fileList") or []
        for item in files if isinstance(files, list) else []:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename") or item.get("path") or "")
            if not filename:
                continue
            extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in audio_exts:
                continue
            parts = re.split(r"[/\\]+", filename)
            parent_text = " ".join(parts[:-1])
            leaf_name = parts[-1]
            samples.append({
                "username": str(username)[:80],
                "filename": filename[:240],
                "album_path_match": album_path_match(album, parent_text),
                "album_filename_match": album_path_match(album, leaf_name),
                "artist_path_match": music_key(artist) in music_key(parent_text),
            })
            if len(samples) >= limit:
                return samples
    return samples


def extract_candidates(payload, artist, album, priority, expected_track_count=None, *, music_key, album_path_match, quality_tier, track_identity):
    import re
    from collections import defaultdict
    audio_exts = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape"}
    def norm(value):
        return music_key(str(value or ""))
    groups = defaultdict(list)
    for response in payload if isinstance(payload, list) else []:
        username = response.get("username") or response.get("user") or ""
        speed = response.get("uploadSpeed") or response.get("averageSpeed") or response.get("speed") or 0
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            speed = 0
        files = response.get("files") or response.get("fileList") or []
        for file_record in files if isinstance(files, list) else []:
            filename = str(file_record.get("filename") or file_record.get("path") or "")
            if not filename or "/" not in filename and "\\" not in filename:
                continue
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in audio_exts:
                continue
            path_parts = re.split(r"[/\\]+", filename)
            path_text = " ".join(path_parts[:-1])
            file_text = path_parts[-1]
            # Require a useful album-level match; filenames alone are weak evidence.
            album_in_path = album_path_match(album, path_text)
            artist_in_path = norm(artist) in norm(path_text)
            title_match = album_path_match(album, file_text)
            artist_match = norm(artist) in norm(path_text + " " + file_text)
            if not (album_in_path or title_match):
                continue
            parent_path = "/".join(path_parts[:-1])
            folder_key = (username, parent_path.casefold())
            rank, tier = quality_tier(file_record, filename, priority)
            try:
                size = int(file_record.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            groups[folder_key].append({
                "filename": filename,
                "size": size,
                "quality_tier": tier,
                "quality_rank": rank,
                "upload_speed": speed,
                "artist_match": artist_match or artist_in_path,
                "album_match": album_in_path or title_match,
                "artist_in_path": artist_in_path,
                "album_in_path": album_in_path,
            })
    candidates = []
    for (username, folder_path), files in groups.items():
        # If the same track is advertised more than once in a folder, retain one
        # copy: highest-priority quality tier, then largest file size as tie-break.
        best_by_track = {}
        for item in files:
            track_key = track_identity(item["filename"])
            if not track_key:
                continue
            previous = best_by_track.get(track_key)
            if (previous is None
                    or (item["quality_rank"], -item["size"]) <
                       (previous["quality_rank"], -previous["size"])):
                best_by_track[track_key] = item
        files = list(best_by_track.values())
        tiers = [item["quality_rank"] for item in files if item["quality_rank"] <= len(priority)]
        avg_rank = sum(tiers) / len(tiers) if tiers else len(priority) + 1
        artist_evidence = any(item["artist_match"] or item["artist_in_path"] for item in files)
        album_evidence = any(item["album_match"] for item in files)
        unique_tracks = {
            track_identity(item["filename"])
            for item in files
            if track_identity(item["filename"])
        }
        unique_track_count = len(unique_tracks)
        # Allow modest search/catalog mismatch: require at least 70% of an expected
        # track count (minimum 3), or 5 unique tracks when catalog count is unknown.
        # This still rejects tiny partial folders without blocking short releases.
        minimum_required = (
            max(3, (int(expected_track_count) * 7 + 9) // 10)
            if expected_track_count else 5
        )
        score = 0.55 * (1.0 if any(x["album_in_path"] for x in files) else 0.65)
        score += 0.25 * (1.0 if any(x["artist_match"] for x in files) else 0.0)
        score += 0.20 * min(unique_track_count / 8.0, 1.0)
        complete_enough = unique_track_count >= minimum_required
        candidates.append({
            "username": username,
            "folder": folder_path.rsplit("/", 1)[-1],
            "file_count": len(files),
            "unique_track_count": unique_track_count,
            "expected_track_count": expected_track_count,
            "complete_enough": complete_enough,
            "files": files,
            "average_quality_rank": round(avg_rank, 3),
            "upload_speed": max((x["upload_speed"] for x in files), default=0),
            "confidence": round(score, 3),
            "clear_match": bool(artist_evidence and album_evidence and complete_enough and score >= 0.72),
            "eligibility_reason": (
                "eligible" if artist_evidence and album_evidence and complete_enough and score >= 0.72
                else f"only {unique_track_count} unique tracks; need at least {minimum_required}"
                if not complete_enough else "album/artist match confidence below threshold"
            ),
            "quality_summary": sorted({
                item["quality_tier"] for item in files
            }),
        })
    candidates.sort(key=lambda item: (
        not item["clear_match"],
        item["average_quality_rank"],
        -item["upload_speed"],
        -item["confidence"],
        -item["file_count"],
    ))
    return candidates
