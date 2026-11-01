"""Pure resolution of the application's persistent data directory."""
from pathlib import Path
from typing import Mapping


def resolve_data_dir(environ: Mapping[str, str], source_file: str | Path) -> Path:
    """Resolve the configured data directory without creating it.

    The legacy NAVIDROME_LIBRARIAN_DATA_DIR name is still read when DISCAIR_DATA_DIR
    is empty or absent. If neither is set, the data directory falls back to the
    directory containing the application source file.
    """
    configured = environ.get("DISCAIR_DATA_DIR") or environ.get("NAVIDROME_LIBRARIAN_DATA_DIR")
    return Path(configured or Path(source_file).resolve().parent).expanduser()
