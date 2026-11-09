"""Waveform peaks for the player's sound graph: decoded once on the server, kept in SQLite, served as about 2 KB per song."""
from .peaks import BINS, PeakService, PeaksUnavailable, compute_peaks

__all__ = ["BINS", "PeakService", "PeaksUnavailable", "compute_peaks"]
