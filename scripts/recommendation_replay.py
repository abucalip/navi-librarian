"""Run offline recommendation replay metrics on a frozen JSON fixture."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from recommendation.diagnostics import evaluate_replay_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", default="tests/fixtures/recommendation_replay.json")
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    print(json.dumps(evaluate_replay_fixture(fixture, k=args.k), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
