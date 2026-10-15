"""Prepare bounded acquisition records passed to the import watcher."""


def prepare_candidate_for_monitor(candidate, fallback_candidates):
    """Copy a selected source into the stable, minimal watcher payload shape.

    slskd search candidates may carry additional metadata. The watcher persists
    the selected file identity and quality summary, while fallback candidates
    retain their metadata but only the filename/size pairs needed for a safe
    source switch. Input dictionaries are never mutated.
    """
    selected = dict(candidate)
    selected["files"] = [
        {"filename": item["filename"], "size": item["size"]}
        for item in candidate["files"]
    ]
    selected["quality_summary"] = list(candidate.get("quality_summary") or [])
    selected["fallback_candidates"] = [
        {
            **item,
            "files": [
                {"filename": file["filename"], "size": file["size"]}
                for file in item.get("files", [])
            ],
        }
        for item in fallback_candidates
    ]
    return selected
