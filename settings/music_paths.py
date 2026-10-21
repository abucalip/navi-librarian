"""Pure policy for choosing the configured music library path."""
from pathlib import Path


def default_music_dir(environ, is_dir):
    """Choose an explicit override or the first available host mount."""
    configured = environ.get("NAVIDROME_MUSIC_DIR")
    if configured:
        return Path(configured).expanduser()
    server_path = Path("/media/library/music")
    mac_path = Path("/Volumes/media/library/music")
    if is_dir(server_path):
        return server_path
    if is_dir(mac_path):
        return mac_path
    # The production deployment is the media LXC; this is its default.
    return server_path
