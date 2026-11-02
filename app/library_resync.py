"""Wire the post-import library resync to the running Librarian service."""
from __future__ import annotations

from acquisition import import_hooks
from discovery import library_resync, store as discovery_store
from settings.service import library_resync_enabled_value, navidrome_generation


def resync_library(librarian) -> None:
    """Drop the cached library snapshot and rebuild the owned index from Navidrome."""
    from app.api.search import owned_index_for

    generation = navidrome_generation(librarian._discovery_settings_read)
    discovery_store.delete_list(librarian.DISCOVERY_DB, f"library_snapshot:navidrome{generation}")
    owned_index_for(librarian).refresh(generation)


def install(get_librarian) -> library_resync.LibraryResync:
    """Register the resync as an import listener. ``get_librarian`` is resolved at call time."""
    resync = library_resync.LibraryResync(
        enabled=lambda: library_resync_enabled_value(get_librarian()._discovery_settings_read),
        resync=lambda: resync_library(get_librarian()),
    )
    import_hooks.register(resync.on_imported)
    return resync
