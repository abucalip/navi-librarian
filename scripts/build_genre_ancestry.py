"""Build settings/genre_ancestry.json: genre tag -> root family, from Wikidata.

Offline at runtime; run this by hand to extend the table. For each tag it
resolves a Wikidata music-genre item, walks "subclass of" (P279) and "part of" (P361) parents
breadth-first, and records the nearest root genre. Reads tags, one per line,
from the files named on the command line. Public read-only requests only.

    python scripts/build_genre_ancestry.py tags.txt [more.txt ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

OUTPUT = Path(__file__).resolve().parent.parent / "settings" / "genre_ancestry.json"
UA = {"User-Agent": "navi-librarian-genre-ancestry/0.1 (+https://github.com/abucalip/navi-librarian)"}
# Wikidata root item -> family key. Order breaks ties between equally near roots.
ROOTS = {
    "Q8341": "jazz", "Q11401": "hip-hop", "Q9778": "electronic",
    "Q38848": "metal", "Q3071": "punk", "Q11399": "rock", "Q37073": "pop",
    "Q9730": "classical", "Q43343": "folk", "Q9759": "blues",
    "Q83440": "country", "Q9794": "reggae", "Q45981": "rnb-soul",
    "Q131272": "rnb-soul", "Q164444": "funk",
}
MAX_DEPTH = 8
_GENRE_WORDS = ("genre", "music", "style", "subgenre", "movement")


def _get(client: httpx.Client, url: str, params: dict) -> dict:
    for attempt in range(3):
        response = client.get(url, params=params, headers=UA, timeout=40)
        if response.status_code == 200:
            return response.json()
        time.sleep(2 * (attempt + 1))
    response.raise_for_status()
    return {}


def resolve(client: httpx.Client, tag: str) -> str | None:
    data = _get(client, "https://www.wikidata.org/w/api.php", {
        "action": "wbsearchentities", "search": tag, "language": "en",
        "type": "item", "limit": 6, "format": "json",
    })
    for hit in data.get("search", []):
        description = str(hit.get("description") or "").casefold()
        if any(word in description for word in _GENRE_WORDS):
            return hit["id"]
    return None


def parents(client: httpx.Client, qids: list[str]) -> dict[str, list[str]]:
    values = " ".join(f"wd:{q}" for q in qids)
    data = _get(client, "https://query.wikidata.org/sparql", {
        "query": f"SELECT ?c ?p WHERE {{ VALUES ?c {{ {values} }} ?c (wdt:P279|wdt:P361) ?p . }}",
        "format": "json",
    })
    result: dict[str, list[str]] = {}
    for row in data["results"]["bindings"]:
        child = row["c"]["value"].rsplit("/", 1)[-1]
        parent = row["p"]["value"].rsplit("/", 1)[-1]
        result.setdefault(child, []).append(parent)
    return result


def nearest_roots(client: httpx.Client, qids: set[str]) -> dict[str, str]:
    """Map each qid to the family of its nearest root ancestor (or itself)."""
    found: dict[str, str] = {}
    cache: dict[str, list[str]] = {}
    frontier = {q: {q} for q in qids}  # current node -> origin qids
    for _ in range(MAX_DEPTH + 1):
        # Equally near roots are ordered by ROOTS, so the first-listed wins.
        for node in sorted(frontier, key=lambda n: list(ROOTS).index(n) if n in ROOTS else len(ROOTS)):
            if node in ROOTS:
                for origin in frontier[node]:
                    found.setdefault(origin, ROOTS[node])
        frontier = {
            n: {o for o in origins if o not in found}
            for n, origins in frontier.items() if n not in ROOTS
        }
        frontier = {n: o for n, o in frontier.items() if o}
        if not frontier:
            break
        uncached = [n for n in frontier if n not in cache]
        for start in range(0, len(uncached), 40):
            batch = uncached[start:start + 40]
            cache.update({n: [] for n in batch})
            cache.update(parents(client, batch))
            time.sleep(1)
        next_frontier: dict[str, set[str]] = {}
        for node, origins in frontier.items():
            for up in cache.get(node, []):
                next_frontier.setdefault(up, set()).update(origins)
        frontier = next_frontier
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag_files", nargs="+")
    args = parser.parse_args(argv)
    tags = sorted({line.strip().casefold() for f in args.tag_files
                   for line in Path(f).read_text(encoding="utf-8").splitlines() if line.strip()})
    existing = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    table = dict(existing.get("tags", {}))
    todo = [t for t in tags if t not in table]
    with httpx.Client() as client:
        qid_by_tag = {}
        for tag in todo:
            qid = resolve(client, tag)
            if qid:
                qid_by_tag[tag] = qid
            time.sleep(0.3)
        roots = nearest_roots(client, set(qid_by_tag.values()))
    for tag, qid in qid_by_tag.items():
        if qid in roots:
            table[tag] = roots[qid]
    OUTPUT.write_text(json.dumps({
        "source": "Wikidata P279 ancestry; generated by scripts/build_genre_ancestry.py",
        "generated": date.today().isoformat(),
        "tags": dict(sorted(table.items())),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(todo)} new tags, {len(qid_by_tag)} resolved, {len(table)} in table", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
