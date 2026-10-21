"""slskd download-transfer listing and remote-directory normalization."""

from urllib.parse import quote


def download_transfer_files(base_url, headers, username, *, http_client):
    """Fetch a peer's tracked files and retain each file's remote directory.

    The HTTP client is injected so this module can be tested without network access
    or importing the application service.
    """
    response = http_client.get(
        f"{base_url}/api/v0/transfers/downloads/"
        f"{quote(str(username), safe='')}",
        headers=headers,
        timeout=8,
    )
    # slskd can remove a peer's transfer entry after transfers finish or disappear.
    # A 404 means there are no currently tracked files for this peer, not that the
    # watcher failed; it still checks the completed-download filesystem every poll.
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        roots = payload
    elif isinstance(payload, dict):
        roots = payload.get("directories") or payload.get("items") or [payload]
    else:
        roots = []

    found = []

    def add_files(directory_record, fallback_directory=None):
        if not isinstance(directory_record, dict):
            return

        remote_directory = directory_record.get("directory") or fallback_directory
        for file_record in directory_record.get("files") or []:
            if not isinstance(file_record, dict):
                continue
            # Return a copy; do not mutate the API response.
            item = dict(file_record)
            item["_transfer_directory"] = (
                str(remote_directory) if remote_directory is not None else None
            )
            found.append(item)

        for child in directory_record.get("directories") or []:
            if isinstance(child, dict):
                add_files(child, remote_directory)

    for root in roots:
        if isinstance(root, dict):
            add_files(root)

    return found


def queue_download_files(base_url, headers, username, selected_files, *, http_client):
    """Queue selected files for a peer and propagate slskd HTTP failures.

    The caller owns dismissal/transition locking; this function only performs the
    remote request so its URL, payload, and error behavior can be tested directly.
    """
    response = http_client.post(
        f"{base_url}/api/v0/transfers/downloads/{username}",
        headers=headers,
        json=selected_files,
        timeout=12,
    )
    response.raise_for_status()
    return response


def match_expected_transfer_records(expected_files, tracked):
    """Match slskd records to expected files by normalized basename.

    When duplicate records identify the same expected basename, prefer completed
    states over active transfers and active transfers over other states.
    Returns the expected-file map and the selected tracked-record map.
    """
    def basename(value):
        return str(value or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()

    def state_rank(value):
        state = str(value or "").replace("_", "").casefold()
        if state in {"succeeded", "completed"}:
            return 2
        if state in {"inprogress", "transferring", "downloading"}:
            return 1
        return 0

    expected_by_name = {}
    for item in expected_files:
        name = basename(item.get("filename"))
        if name:
            expected_by_name[name] = item

    tracked_by_name = {}
    for item in tracked:
        name = basename(item.get("filename"))
        if name not in expected_by_name:
            continue
        prior = tracked_by_name.get(name)
        if prior is None or state_rank(item.get("state")) >= state_rank(prior.get("state")):
            tracked_by_name[name] = item

    return expected_by_name, tracked_by_name


def summarize_transfer_progress(expected_by_name, tracked_by_name):
    """Aggregate matched expected/tracked records without touching shared state.

    Completed-state records count as complete even when byte counters are absent.
    A non-completed record whose reported bytes reach a known file size also counts
    as complete. Speed snapshots use only real transfer counters, not inferred
    bytes for completed files.
    """
    completed_states = {"succeeded", "completed"}
    completed = 0
    total_bytes = 0
    transferred_bytes = 0
    file_byte_snapshot = {}

    for name, expected in expected_by_name.items():
        item = tracked_by_name.get(name) or {}
        state = str(item.get("state") or "").replace("_", "").casefold()
        is_completed_state = state in completed_states
        if is_completed_state:
            completed += 1

        try:
            size = max(0, int(expected.get("size") or item.get("size") or 0))
        except (TypeError, ValueError):
            size = 0
        transferred = 0
        raw_transferred = 0
        has_transfer_counter = False
        for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes"):
            if item.get(key) is not None:
                try:
                    raw_transferred = max(0, int(item[key]))
                    transferred = raw_transferred
                    has_transfer_counter = True
                    break
                except (TypeError, ValueError):
                    pass
        if is_completed_state and size:
            transferred = size
        if size:
            transferred = min(transferred, size)
            total_bytes += size
            transferred_bytes += transferred
            if transferred >= size and not is_completed_state:
                completed += 1
        file_byte_snapshot[name] = raw_transferred if has_transfer_counter else 0

    return {
        "total_tracks": len(expected_by_name),
        "completed_tracks": min(completed, len(expected_by_name)),
        "total_size_bytes": total_bytes,
        "transferred_size_bytes": transferred_bytes,
        "file_byte_snapshot": file_byte_snapshot,
    }


def estimate_transfer_speed(current_files, prior_snapshot, now):
    """Estimate bytes/second from two actual-counter snapshots.

    Missing baselines and intervals shorter than half a second return None.
    Counter resets are treated as zero progress; inferred completion bytes
    must not be included in current_files.
    """
    if not prior_snapshot:
        return None
    elapsed = now - prior_snapshot["at"]
    if elapsed < 0.5:
        return None
    delta = sum(
        max(0, value - int(prior_snapshot["files"].get(name, 0)))
        for name, value in current_files.items()
    )
    return int(delta / elapsed)
