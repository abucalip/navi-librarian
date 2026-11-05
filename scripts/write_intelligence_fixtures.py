"""Write the Server V2 contract fixtures to intelligence/contract-fixtures.

Run from the repository root: ``python scripts/write_intelligence_fixtures.py``.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intelligence.api.fixture_set import build_fixtures  # noqa: E402

OUT = ROOT / "intelligence" / "contract-fixtures"


def render(document):
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, document in build_fixtures().items():
        (OUT / name).write_text(render(document), encoding="utf-8")
        print("wrote", name)
