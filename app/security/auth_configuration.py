"""Pure application-authentication configuration policy."""


def auth_is_configured(settings):
    """Return whether the persisted settings contain all required owner credentials."""
    return bool(
        settings.get("app_auth_username")
        and settings.get("app_auth_salt")
        and settings.get("app_auth_hash")
    )
