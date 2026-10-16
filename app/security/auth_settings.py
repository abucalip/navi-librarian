"""Lazy access to persisted settings used by app authentication."""


class AuthSettingsReader:
    """Read the current persisted settings through an injected owner getter.

    The reader deliberately does not cache: setup and credential changes must
    be visible to middleware and auth routes on the next read.
    """

    def __init__(self, *, settings_getter):
        self._settings_getter = settings_getter

    def get(self):
        """Return the current settings mapping without copying or caching it."""
        return self._settings_getter()
