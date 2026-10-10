from pathlib import Path
from datetime import datetime
import py_compile
import shutil

source = Path("navidrome_server.py")

if not source.exists():
    raise SystemExit("ERROR: navidrome_server.py not found.")

original = source.read_text(encoding="utf-8")
updated = original

replacements = [
    (
        "for index, item in enumerate(recommendations[:70]):",
        "for index, item in enumerate(recommendations[:100]):",
    ),
    (
        "if len(artist_ids) >= 18:",
        "if len(artist_ids) >= 40:",
    ),
    (
        '''    candidates_by_category = {
        "adjacent": [],
        "cross_genre": [],
        "adventurous": [],
    }''',
        '''    candidates_by_category = {
        "adjacent": [],
        "cross_genre": [],
        "adventurous": [],
        "unclassified": [],
    }''',
    ),
    (
        '''        if core_overlap and (families - core_overlap):
            category = "cross_genre"
        elif core_overlap or exploration_overlap:
            category = "adjacent"
        else:
            # Missing tags are still marked as low-confidence below.
            category = "adventurous"''',
        '''        if not tags:
            # Missing metadata is unknown, not evidence of adventurousness.
            category = "unclassified"
        elif core_overlap and (families - core_overlap):
            category = "cross_genre"
        elif core_overlap or exploration_overlap:
            category = "adjacent"
        else:
            # Tags exist, but do not map to our current musical families.
            category = "adventurous"''',
    ),
    (
        '''                    "adventurous": "This candidate broadens the selection "
                                   "beyond the strongest genre matches."
                }[category]''',
        '''                    "adventurous": "Available genre tags suggest a "
                                   "departure from the strongest mapped "
                                   "genre matches.",
                    "unclassified": "Genre metadata is unavailable, so this "
                                    "candidate's musical fit is uncertain."
                }[category]''',
    ),
    (
        '''            "Only the first 70 ListenBrainz recording recommendations are resolved.",''',
        '''            "Up to the first 100 ListenBrainz recording recommendations are resolved.",''',
    ),
    (
        '''            "Genre tags are community-supplied and may be missing or incomplete.",''',
        '''            "Genre tags are community-supplied and may be missing or incomplete.",
            "Candidates without genre tags are classified as unclassified, not adventurous.",
            "Genre tags are retrieved for up to 40 artists from the highest-scoring resolved candidates.",''',
    ),
]

for old, new in replacements:
    count = updated.count(old)
    if count != 1:
        raise SystemExit(
            f"ABORTED: Expected one occurrence, found {count} for:\n{old[:180]}"
        )
    updated = updated.replace(old, new, 1)

backup = source.with_name(
    f"{source.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
)
shutil.copy2(source, backup)

source.write_text(updated, encoding="utf-8")

try:
    py_compile.compile(str(source), doraise=True)
except Exception:
    shutil.copy2(backup, source)
    raise SystemExit(
        f"Compilation failed. Original file restored from {backup}."
    )

print("Patch applied successfully.")
print(f"Backup: {backup}")
print("Changes:")
print("- Recording resolution limit: 70 -> 100")
print("- Artist genre lookup limit: 18 -> 40")
print("- Missing genre metadata now produces 'unclassified'")
print("- Adventurous classification now requires available genre tags")
print("- Python syntax check passed")
