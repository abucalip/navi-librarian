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
