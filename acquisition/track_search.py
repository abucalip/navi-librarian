"""Pure slskd query and candidate selection for a single-song Get.

A song is chosen only when one advertised file clearly is that song by that artist: the title
must be the whole of the file name once the track number, the artist and the album are set
aside, and neither the file name nor its folders may mark another version (live, remix,
karaoke and so on) the requested title does not carry. Nothing here touches the network.
"""
from __future__ import annotations

import re
from typing import Any, Callable

AUDIO_EXTENSIONS = frozenset({".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape"})

# A word that names another recording of the song. Refused when the requested title lacks it.
VERSION_WORDS = frozenset({
    "live", "remix", "remixed", "mix", "instrumental", "karaoke", "acoustic", "demo", "cover",
    "edit", "version", "session", "sessions", "tribute", "unplugged", "cappella", "dub",
    "rehearsal", "bootleg", "medley", "reprise", "interlude", "skit", "radio", "extended",
    "alternate", "alternative", "outtake", "mashup", "slowed", "sped", "nightcore", "8d",
})
# Words that describe the file rather than the song; they never block a match.
NOISE_WORDS = frozenset({
    "remaster", "remastered", "mono", "stereo", "flac", "mp3", "kbps", "cd", "web", "vinyl",
    "lossless", "320", "256", "192", "128", "v0", "16", "24", "44", "48", "96", "bit", "khz",
    "hq", "official", "audio", "track", "disc", "cd1", "cd2", "deluxe", "bonus", "feat", "ft",
    "featuring", "explicit", "clean", "m4a", "ogg", "opus", "wav",
})


def _tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").casefold())


_EDITION_NOTE = re.compile(r"(?i)remaster|mono|stereo|deluxe|bonus|(?<!\d)(?:19|20)\d{2}(?!\d)")


def core_title(title: str) -> str:
    """The title without edition notes a file name rarely repeats: "(2011 Remaster)", "- Mono"."""
    def note(match):
        return " " if _EDITION_NOTE.search(match.group(0)) else match.group(0)

    stripped = re.sub(r"\s*[\(\[][^)\]]*[\)\]]", note, str(title or ""))
    stripped = re.sub(r"\s+-\s+(?:(?:19|20)\d{2}\s+)?(?:remaster\w*|mono|stereo|deluxe|bonus)\b.*$", " ", stripped, flags=re.I)
    return re.sub(r"\s+", " ", stripped).strip() or str(title or "").strip()


def track_search_queries(artist: str, title: str) -> list[str]:
    """A small, ordered set of Soulseek queries for one song, widest wildcard last."""
    from integrations.slskd.search import masked_artist_variants

    artist = re.sub(r"\s+", " ", str(artist or "")).strip()
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    if not artist or not title:
        return []
    plain_title = re.sub(r"\s*[\(\[][^)\]]*[\)\]]", " ", core_title(title))
    variants = [
        f"{artist} {core_title(title)}",
        *(f"{masked} {core_title(title)}" for masked in masked_artist_variants(artist)),
        f"{artist} {plain_title}",
    ]
    queries: list[str] = []
    seen: set[str] = set()
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query.casefold() not in seen:
            queries.append(query)
            seen.add(query.casefold())
    return queries


def _contains_run(haystack: list[str], needle: list[str]) -> int:
    """Index where ``needle`` first appears as a contiguous run in ``haystack``, or -1."""
    if not needle:
        return -1
    for index in range(len(haystack) - len(needle) + 1):
        if haystack[index:index + len(needle)] == needle:
            return index
    return -1


def file_is_song(filename: str, artist: str, album: str, title: str) -> bool:
    """True when the file name is the requested song and nothing else."""
    parts = re.split(r"[/\\]+", str(filename or ""))
    stem = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", parts[-1])
    # Quality tags are not part of the title: "320kbps", "16bit", "44.1khz".
    stem = re.sub(r"(?i)\b\d{2,3}\s*kbps\b|\b\d{2}\s*-?\s*bit\b|\b\d{2,3}(?:[.,]\d)?\s*khz\b", " ", stem)
    folders = " ".join(parts[:-1])
    title_tokens = _tokens(core_title(title))
    stem_tokens = _tokens(stem)
    start = _contains_run(stem_tokens, title_tokens)
    if start < 0:
        return False
    # A release's own version words never count against it: only those the title and album lack.
    allowed = set(_tokens(title)) | set(_tokens(album)) | set(_tokens(artist))
    versions = VERSION_WORDS - allowed
    if any(token in versions for token in stem_tokens):
        return False
    if any(token in versions for token in _tokens(folders)):
        return False
    leftover = stem_tokens[:start] + stem_tokens[start + len(title_tokens):]
    ignorable = set(_tokens(artist)) | set(_tokens(album)) | NOISE_WORDS
    return all(token.isdigit() or token in ignorable for token in leftover)


def extract_track_candidates(
    payload: list[dict[str, Any]],
    artist: str,
    album: str,
    title: str,
    priority: list[str],
    *,
    music_key: Callable[[str], str],
    album_path_match: Callable[[str, str], bool],
    quality_tier: Callable[[dict[str, Any], str, list[str]], tuple[int, str]],
) -> list[dict[str, Any]]:
    """Single audio files that clearly are the song, best first.

    Only files in a tier the owner prioritised are kept (SET-03). Order: quality tier, then a
    file under the right album, then the peer's upload speed.
    """
    artist_key = music_key(artist)
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for response in payload if isinstance(payload, list) else []:
        username = str(response.get("username") or response.get("user") or "")
        try:
            speed = int(response.get("uploadSpeed") or response.get("averageSpeed") or response.get("speed") or 0)
        except (TypeError, ValueError):
            speed = 0
        files = response.get("files") or response.get("fileList") or []
        for record in files if isinstance(files, list) else []:
            if not isinstance(record, dict):
                continue
            filename = str(record.get("filename") or record.get("path") or "")
            if not username or "/" not in filename and "\\" not in filename:
                continue
            extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in AUDIO_EXTENSIONS:
                continue
            try:
                size = int(record.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            if size <= 0:
                continue
            if artist_key not in music_key(filename):
                continue
            if not file_is_song(filename, artist, album, title):
                continue
            rank, tier = quality_tier(record, filename, priority)
            if rank > len(priority):
                continue
            parts = re.split(r"[/\\]+", filename)
            found[(username.casefold(), filename.casefold())] = {
                "username": username,
                "filename": filename,
                "size": size,
                "folder": parts[-2] if len(parts) > 1 else "",
                "quality_tier": tier,
                "quality_rank": rank,
                "upload_speed": speed,
                "album_match": album_path_match(album, " ".join(parts[:-1])),
            }
    return sorted(
        found.values(),
        key=lambda item: (item["quality_rank"], not item["album_match"], -item["upload_speed"], -item["size"]),
    )
