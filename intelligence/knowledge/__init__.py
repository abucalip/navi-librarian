"""The one read path to Server V2 knowledge (docs/efficiency.md E5).

Routes, pages and lenses read through :class:`KnowledgeReader`; they do not query tables or call
providers. The package imports no provider client and no web module (tested)."""
from .reader import KnowledgeReader, SLICE_SOURCE, slice_status

__all__ = ["KnowledgeReader", "SLICE_SOURCE", "slice_status"]
