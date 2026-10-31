"""Relay one station stream to one client while reading its song titles."""
from __future__ import annotations

from integrations.radio.icy import IcyParser, stream_title

USER_AGENT = "Discair-Radio/1.0"
UPSTREAM_REQUEST_HEADERS = {"Icy-MetaData": "1", "User-Agent": USER_AGENT, "Accept": "*/*"}
# A playlist or web page is not a stream; relaying it would hand the client a broken station.
REFUSED_TYPES = ("text/", "application/vnd.apple.mpegurl", "application/x-mpegurl",
                 "audio/x-mpegurl", "audio/mpegurl", "audio/x-scpls", "application/pls")


def stream_is_audio(content_type: str) -> bool:
    kind = (content_type or "").split(";")[0].strip().lower()
    return bool(kind) and not kind.startswith(REFUSED_TYPES)


def metaint_of(headers) -> int:
    try:
        return max(int(headers.get("icy-metaint", "0")), 0)
    except ValueError:
        return 0


async def relay_body(upstream, metaint: int, client_wants_metadata: bool, tracker):
    """Yield the bytes for the client; report every title that passes to ``tracker``.

    A client that asked for metadata gets the stream untouched. One that did not gets the
    audio only, since it would play the metadata blocks as noise.
    """
    parser = IcyParser(metaint) if metaint else None
    try:
        async for chunk in upstream.aiter_raw():
            if parser is None:
                yield chunk
                continue
            events = parser.feed(chunk)
            for kind, data in events:
                if kind == "meta":
                    tracker.set_title(stream_title(data))
            if client_wants_metadata:
                yield chunk
            else:
                audio = b"".join(data for kind, data in events if kind == "audio")
                if audio:
                    yield audio
    finally:
        tracker.close()
