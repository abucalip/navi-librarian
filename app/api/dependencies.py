"""Lazy default adapter for web routes that use the legacy librarian service."""


def get_librarian():
    """Resolve the existing service only when a request needs it.

    Keeping the import inside this dependency lets route modules be imported and
    tested with fake services without initializing the MCP server as a side effect.
    """
    import navidrome_server as librarian

    return librarian
