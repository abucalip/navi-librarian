"""MCP tool registration kept separate from the shared librarian service module.

The web application imports navidrome_server as a compatibility service.
Keeping the MCP SDK import and registration here prevents web service use from
initializing the MCP runtime as an import side effect.
"""

TOOL_NAMES = (
    "get_server_source",
    "library_overview",
    "search_music",
    "get_album_details",
    "find_missing_mbids",
    "recent_listening_profile",
    "recommend_new_music",
    "discovery_set_feedback",
    "discovery_get_navidrome_settings",
    "discovery_set_navidrome_settings",
    "discovery_test_navidrome_connection",
    "discovery_get_lastfm_settings",
    "discovery_set_lastfm_settings",
    "discovery_test_lastfm_connection",
    "discovery_get_listenbrainz_settings",
    "discovery_set_listenbrainz_settings",
    "discovery_test_listenbrainz_connection",
    "discovery_get_slskd_settings",
    "discovery_set_slskd_settings",
    "discovery_test_slskd_connection",
    "_discovery_reactivate_dismissed_acquisition",
    "discovery_acquire_album",
    "discovery_queue_slskd_candidate",
    "discovery_get_list",
    "discovery_refresh_list",
)


def create_mcp_server(librarian_module, server_class=None):
    """Register legacy tool functions on an MCP server instance.

    server_class is injectable so the registry can be tested without importing
    the MCP SDK. Production imports the SDK only when an MCP server is started.
    """
    if server_class is None:
        from mcp.server.mcpserver import MCPServer

        server_class = MCPServer

    server = server_class("navidrome-librarian")
    for name in TOOL_NAMES:
        server.tool()(getattr(librarian_module, name))
    return server
