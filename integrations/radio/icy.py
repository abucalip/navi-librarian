"""Shoutcast/Icecast in-stream metadata (ICY): block parsing and title splitting."""
from __future__ import annotations

import re

_STREAM_TITLE = re.compile(r"StreamTitle='(.*?)'(?:;|$)", re.DOTALL)
SEPARATOR = " - "


class IcyParser:
    """Split an ICY stream into audio bytes and metadata blocks.

    The server sends ``metaint`` audio bytes, one length byte (times 16), then that many
    metadata bytes, and repeats. ``feed`` accepts arbitrary chunk boundaries and returns
    ``("audio", bytes)`` and ``("meta", bytes)`` events in order. An empty block (length 0,
    meaning "unchanged") produces no event.
    """

    def __init__(self, metaint: int):
        if metaint <= 0:
            raise ValueError("metaint must be positive")
        self.metaint = metaint
        self._audio_left = metaint
        self._expect_length = False
        self._meta_left: int | None = None
        self._meta = bytearray()

    def feed(self, data: bytes) -> list[tuple[str, bytes]]:
        events: list[tuple[str, bytes]] = []
        index, size = 0, len(data)
        while index < size:
            if self._expect_length:
                self._meta_left = data[index] * 16
                self._expect_length = False
                self._meta.clear()
                index += 1
                if self._meta_left == 0:
                    self._finish_block(events)
            elif self._meta_left is not None:
                take = min(self._meta_left, size - index)
                self._meta += data[index:index + take]
                self._meta_left -= take
                index += take
                if self._meta_left == 0:
                    self._finish_block(events)
            else:
                take = min(self._audio_left, size - index)
                events.append(("audio", data[index:index + take]))
                self._audio_left -= take
                index += take
                if self._audio_left == 0:
                    self._expect_length = True
        return events

    def _finish_block(self, events: list[tuple[str, bytes]]) -> None:
        if self._meta:
            events.append(("meta", bytes(self._meta)))
        self._meta_left = None
        self._meta.clear()
        self._audio_left = self.metaint


def stream_title(block: bytes) -> str | None:
    """The ``StreamTitle`` of one metadata block, or None when the block carries none."""
    try:
        text = block.decode("utf-8")
    except UnicodeDecodeError:
        text = block.decode("latin-1")
    found = _STREAM_TITLE.search(text.rstrip("\x00"))
    return found.group(1).strip() if found else None


def split_artist_title(raw: str) -> tuple[str | None, str]:
    """``"Artist - Title"`` into its parts; ``(None, raw)`` when it has no separator."""
    artist, separator, title = raw.partition(SEPARATOR)
    if separator and artist.strip() and title.strip():
        return artist.strip(), title.strip()
    return None, raw.strip()
