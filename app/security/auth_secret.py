"""Lazy, thread-safe loading of the persistent app-auth signing secret."""

from threading import Lock


class AuthSecretProvider:
    """Load a signing secret on first use and cache successful loads only.

    The data-directory lookup is injected so importing this module does not
    initialize the app or read persistent settings.
    """

    def __init__(self, *, data_dir_getter, secret_loader):
        self._data_dir_getter = data_dir_getter
        self._secret_loader = secret_loader
        self._secret = None
        self._lock = Lock()

    def get(self):
        """Return the cached secret, retrying later if loading raises or returns None."""
        if self._secret is None:
            with self._lock:
                if self._secret is None:
                    secret = self._secret_loader(self._data_dir_getter())
                    if secret is not None:
                        self._secret = secret
        return self._secret
