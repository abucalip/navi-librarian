"""Compatibility imports for the packaged Navidrome client.

New production code should import from :mod:`integrations.navidrome.client`.
"""

from integrations.navidrome.client import (  # noqa: F401
    album_details_payload,
    api_call,
    items,
    library_overview_payload,
    search_result_payload,
)
