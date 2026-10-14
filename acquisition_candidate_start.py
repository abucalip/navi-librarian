"""Validate whether a queued slskd candidate has safely started.

All external boundaries are injected so path validation, transfer-state handling,
and conservative cancellation behavior can be tested without initializing the MCP app.
"""
from urllib.parse import quote


def candidate_start_state(
    base_url,
    headers,
    candidate,
    timeout=8,
    *,
    download_transfer_files,
    http_client,
    http_error_types,
    monotonic,
    sleep,
):
    """Return True if started, False if safely stopped/absent, or None if uncertain."""
    def normalized_remote_path(value):
        value = str(value or "").replace("\\", "/")
        parts = [part for part in value.split("/") if part not in ("", ".")]
        if any(part == ".." for part in parts):
            return None
        return "/".join(parts).casefold()

    expected = set()
    expected_directories = set()
    for item in candidate.get("files", []):
        filename = str(item.get("filename") or "").replace("\\", "/")
        normalized = normalized_remote_path(filename)
        name = filename.rsplit("/", 1)[-1].casefold()
        if not name or normalized is None or "/" not in normalized:
            return None
        expected.add(name)
        expected_directories.add(normalized.rsplit("/", 1)[0])
    if len(expected_directories) != 1:
        return None
    expected_directory = next(iter(expected_directories))

    deadline = monotonic() + timeout
    last_files = []
    while monotonic() < deadline:
        try:
            tracked = download_transfer_files(
                base_url, headers, candidate["username"]
            )
        except (*http_error_types, ValueError, TypeError):
            return None
        last_files = []
        for item in tracked:
            filename = str(item.get("filename") or "").replace("\\", "/")
            name = filename.rsplit("/", 1)[-1].casefold()
            if name not in expected:
                continue
            directory = item.get("_transfer_directory")
            if directory is None:
                normalized_filename = normalized_remote_path(filename)
                if normalized_filename is None or "/" not in normalized_filename:
                    return None
                directory = normalized_filename.rsplit("/", 1)[0]
            normalized_directory = normalized_remote_path(directory)
            if normalized_directory is None:
                return None
            if normalized_directory == expected_directory:
                last_files.append(item)
        states = {
            str(item.get("state") or "").replace("_", "").casefold()
            for item in last_files
        }
        if states.intersection({
            "inprogress", "succeeded", "completed", "transferring", "downloading"
        }):
            return True
        if states and states.issubset({
            "failed", "errored", "cancelled", "canceled"
        }):
            return False
        sleep(1)
    if not last_files:
        return False
    queued = [
        item for item in last_files
        if str(item.get("state") or "").replace("_", "").casefold()
        in {"queued", "initializing", "requested"}
    ]
    if not queued:
        return None
    # Do not start another source while the first one's files remain queued.
    # A failed cancellation is uncertain rather than permission to duplicate.
    for item in queued:
        file_id = str(item.get("id") or item.get("filename") or "")
        if not file_id:
            return None
        try:
            cancelled = http_client.delete(
                f"{base_url}/api/v0/transfers/downloads/"
                f"{quote(str(candidate['username']), safe='')}/"
                f"{quote(file_id, safe='')}",
                headers=headers,
                timeout=6,
            )
            if cancelled.status_code not in (200, 202, 204, 404):
                return None
        except http_error_types:
            return None
    return False
