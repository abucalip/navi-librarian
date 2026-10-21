from pathlib import Path
from datetime import datetime
import py_compile
import shutil

path = Path("navidrome_server.py")
source = path.read_text(encoding="utf-8")

marker = '    return json.dumps({\n        "source": "ListenBrainz + MusicBrainz + Navidrome",'

if source.count(marker) != 1:
    raise SystemExit(
        "ABORTED: Could not uniquely locate the recommendation return block."
    )

diagnostic_code = '''    # Temporary diagnostics: inspect all resolved candidates before return.
    candidate_debug = []
    candidate_category_counts = Counter()

    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        families = genre_families(tags)

        if not tags:
            category = "unclassified"
        elif families & core_families and (
            families - (families & core_families)
        ):
            category = "cross_genre"
        elif families & core_families or families & exploration_families:
            category = "adjacent"
        else:
            category = "adventurous"

        title_key = _music_key(candidate["album"])
        same_title = library_by_title.get(title_key, [])
        exact_owned = any(
            _music_key(match.get("artist", ""))
            == _music_key(candidate["primary_artist"])
            for match in same_title
        )

        candidate_category_counts[category] += 1

        candidate_debug.append({
            "artist": candidate["artist"],
            "album": candidate["album"],
            "score": candidate["score"],
            "discovery_score": round(
                candidate.get("discovery_score", 0), 6
            ),
            "genre_tags": tags,
            "genre_families": sorted(families),
            "assigned_category": category,
            "genre_metadata_available": bool(tags),
            "exact_owned": exact_owned,
            "same_title_library_matches": len(same_title),
            "already_selected_artist": (
                _music_key(candidate["primary_artist"])
                in artist_recommendation_counts
            ),
        })

    candidate_debug.sort(
        key=lambda item: item["discovery_score"],
        reverse=True,
    )

'''

updated = source.replace(marker, diagnostic_code + marker, 1)

payload_marker = '        "recommendations": found,'
if updated.count(payload_marker) != 1:
    raise SystemExit("ABORTED: Could not uniquely locate recommendations field.")

updated = updated.replace(
    payload_marker,
    payload_marker + '''
        "debug_candidate_category_counts": dict(candidate_category_counts),
        "debug_all_candidates": candidate_debug,
''',
    1,
)

backup = path.with_name(
    f"{path.name}.bak-diagnostics-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
)
shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

try:
    py_compile.compile(str(path), doraise=True)
except Exception as exc:
    shutil.copy2(backup, path)
    raise SystemExit(f"Compilation failed; original restored. {exc}")

print("Diagnostic patch applied; Python syntax check passed.")
print(f"Backup: {backup}")
print("The recommendation algorithm itself was not changed.")
