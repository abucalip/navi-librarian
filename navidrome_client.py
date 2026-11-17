"""Compatibility imports for the packaged Navidrome client.

New production code should import from :mod:`integrations.navidrome.client`.
"""

from integrations.navidrome.client import (  # noqa: F401
    api_call,
    items,
)
