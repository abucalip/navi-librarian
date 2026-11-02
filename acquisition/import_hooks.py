"""Listeners told when an album or song import has finished.

The import code calls ``notify_imported`` after it stores the ``imported`` status. A listener
never changes the import: an exception in a listener is swallowed, so a slow or broken
follow-up (such as a library resync) cannot turn a finished import into a failed one.
"""
from __future__ import annotations

from typing import Callable

_listeners: list[Callable[[str, str], None]] = []


def register(listener: Callable[[str, str], None]) -> None:
    """Add a listener once; registering the same function again does nothing."""
    if listener not in _listeners:
        _listeners.append(listener)


def notify_imported(artist: str, album: str) -> None:
    """Tell every listener that ``artist`` / ``album`` has just been imported."""
    for listener in list(_listeners):
        try:
            listener(artist, album)
        except Exception:
            pass
