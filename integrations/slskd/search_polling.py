"""Dependency-injected slskd query polling and peer-payload collection."""

import json


def collect_search_responses(
    search_queries,
    base_url,
    headers,
    *,
    http_client,
    monotonic,
    sleep,
    new_search_id,
    response_items,
    overall_timeout=45,
):
    """Run progressive slskd queries and wait for advertised peer payloads.

    HTTP, clock, sleep, ID generation, and response normalization are injected so
    retry/wait behavior can be tested without a running slskd service.
    HTTP and unexpected payload errors intentionally propagate to the caller.
    """
    search_id = new_search_id()
    search_deadline = monotonic() + overall_timeout
    search_attempts = []
    reported_response_count = 0
    reported_file_count = 0
    payload_by_peer = {}

    for query_index, query in enumerate(search_queries):
        if monotonic() >= search_deadline:
            break
        search_timeout_ms = 15000 if query_index == 0 else 6000
        search_id = new_search_id()
        response = http_client.post(
            base_url + "/api/v0/searches",
            headers=headers,
            json={
                "id": search_id,
                "searchText": query,
                "fileLimit": 1000,
                "filterResponses": True,
                "maximumPeerQueueLength": 100,
                "minimumResponseFileCount": 1,
                "minimumPeerUploadSpeed": 0,
                "responseLimit": 100,
                "searchTimeout": search_timeout_ms,
            },
            timeout=10,
        )
        response.raise_for_status()
        deadline = min(
            monotonic() + (18 if query_index == 0 else 8),
            search_deadline,
        )
        completed_without_payload_since = None
        attempt_reported_response_count = 0
        attempt_reported_file_count = 0
        attempt_payload_by_peer = {}
        last_state = ""

        while monotonic() < deadline:
            search_state = {}
            try:
                state_response = http_client.get(
                    f"{base_url}/api/v0/searches/{search_id}",
                    params={"includeResponses": "true"},
                    headers=headers,
                    timeout=8,
                )
                state_response.raise_for_status()
                state_data = state_response.json()
                if isinstance(state_data, dict):
                    search_state = state_data
                    try:
                        attempt_reported_response_count = max(
                            attempt_reported_response_count,
                            int(state_data.get("responseCount") or state_data.get("response_count") or 0),
                        )
                        attempt_reported_file_count = max(
                            attempt_reported_file_count,
                            int(state_data.get("fileCount") or state_data.get("file_count") or 0),
                        )
                    except (TypeError, ValueError):
                        pass
                    for entry in response_items(state_data):
                        files = entry.get("files") or entry.get("fileList") or []
                        if not isinstance(files, list) or not files:
                            continue
                        identity = (
                            entry.get("username") or entry.get("user") or "",
                            json.dumps(files, sort_keys=True, ensure_ascii=False),
                        )
                        attempt_payload_by_peer[identity] = entry
            except http_client.HTTPStatusError as exc:
                if exc.response.status_code not in (404, 405):
                    raise

            response_poll = http_client.get(
                f"{base_url}/api/v0/searches/{search_id}/responses",
                headers=headers,
                timeout=8,
            )
            if response_poll.status_code not in (404, 405):
                response_poll.raise_for_status()
                data = response_poll.json()
                for entry in response_items(data):
                    files = entry.get("files") or entry.get("fileList") or []
                    if not isinstance(files, list) or not files:
                        continue
                    identity = (
                        entry.get("username") or entry.get("user") or "",
                        json.dumps(files, sort_keys=True, ensure_ascii=False),
                    )
                    attempt_payload_by_peer[identity] = entry

            state_text = str(search_state.get("state") or "").lower()
            last_state = state_text or (
                "complete" if search_state.get("isComplete") is True else last_state
            )
            is_complete = search_state.get("isComplete") is True or (
                state_text and ("complete" in state_text or "timedout" in state_text)
            )
            if is_complete:
                if attempt_payload_by_peer:
                    break
                if attempt_reported_response_count > 0:
                    if completed_without_payload_since is None:
                        completed_without_payload_since = monotonic()
                    elif monotonic() - completed_without_payload_since >= 3:
                        break
                    sleep(0.5)
                    continue
                break

            # Counts may arrive before slskd exposes the peer file lists. Do not
            # spend the remaining search budget on a broader query while polling.
            if attempt_reported_response_count > 0 and not attempt_payload_by_peer:
                deadline = search_deadline
            sleep(0.75)

        reported_response_count = max(reported_response_count, attempt_reported_response_count)
        reported_file_count = max(reported_file_count, attempt_reported_file_count)
        search_attempts.append({
            "query": query,
            "search_id": search_id,
            "state": last_state or "unknown",
            "slskd_reported_response_count": attempt_reported_response_count,
            "slskd_reported_file_count": attempt_reported_file_count,
            "collected_peer_response_count": len(attempt_payload_by_peer),
        })
        if attempt_payload_by_peer:
            payload_by_peer = attempt_payload_by_peer
            break

    return {
        "search_id": search_id,
        "search_attempts": search_attempts,
        "reported_response_count": reported_response_count,
        "reported_file_count": reported_file_count,
        "payload_by_peer": payload_by_peer,
    }
