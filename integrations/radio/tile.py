"""Generated station tile: the station's initials on a colour hashed from its name, as a PNG.

Pure Python (zlib and struct), so no image library is needed. A 5x7 pixel font covers A-Z and 0-9.
"""
from __future__ import annotations

import hashlib
import struct
import zlib

_GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
}

# Dark enough that white initials stay readable on every colour.
_PALETTE = [
    (0x1F, 0x4E, 0x79), (0x6A, 0x1B, 0x9A), (0x8E, 0x24, 0x3B), (0x2E, 0x7D, 0x32),
    (0xB2, 0x5B, 0x00), (0x00, 0x6D, 0x77), (0x4A, 0x3F, 0x8F), (0x9C, 0x27, 0x6B),
    (0x37, 0x47, 0x4F), (0x5D, 0x40, 0x37),
]
_FOREGROUND = (0xFF, 0xFF, 0xFF)


def initials(name: str) -> str:
    """Up to two characters: the first letter of the first two words, else the first two characters."""
    words = [word for word in "".join(c if c.isalnum() else " " for c in (name or "")).split() if word]
    letters = "".join(word[0] for word in words[:2]) if len(words) > 1 else "".join(words)[:2]
    letters = letters.upper()
    return letters if letters else "R"


def colour_for(name: str) -> tuple[int, int, int]:
    digest = hashlib.sha256((name or "").encode("utf-8")).digest()
    return _PALETTE[digest[0] % len(_PALETTE)]


def tile_png(name: str, size: int) -> bytes:
    if size <= 0:
        raise ValueError("size must be positive")
    text = [_GLYPHS.get(ch, _GLYPHS["R"]) for ch in initials(name)]
    scale = max(1, size // 20)
    glyph_w, glyph_h, gap = 5 * scale, 7 * scale, scale
    text_w = len(text) * glyph_w + (len(text) - 1) * gap
    left = (size - text_w) // 2
    top = (size - glyph_h) // 2

    background = bytes(colour_for(name))
    foreground = bytes(_FOREGROUND)
    rows = []
    for y in range(size):
        row = bytearray(background * size)
        if top <= y < top + glyph_h:
            glyph_row = (y - top) // scale
            x = left
            for glyph in text:
                line = glyph[glyph_row]
                for col, cell in enumerate(line):
                    if cell == "#":
                        start = (x + col * scale) * 3
                        row[start:start + scale * 3] = foreground * scale
                x += glyph_w + gap
        rows.append(b"\x00" + bytes(row))
    return _png(size, size, b"".join(rows))


def _png(width: int, height: int, raw_rows: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB, no interlace
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw_rows, 6)) + chunk(b"IEND", b""))
