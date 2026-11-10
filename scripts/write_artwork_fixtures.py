"""Write the artwork index contract fixtures (docs/artwork.md, slice 1) by calling the real route.

Each file is `GET /api/artwork/index` answered by the real route, service, index merge and store, with
the MusicBrainz and CAA fetchers replaced by canned answers. The ids, dates and comments are invented
(no provider traffic, no owner data), so shapes are exact and values are not real. Re-run after a body
change; tests/test_artwork_fixtures.py fails if the files drift from what the route returns.

    python scripts/write_artwork_fixtures.py
"""
from __future__ import annotations

import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.api.artwork as routes  # noqa: E402
from intelligence.artwork import ArtworkService, ArtworkStore  # noqa: E402
from intelligence.artwork.service import _trim_doc  # noqa: E402
from intelligence.artwork.index import EMPTY, OK, UNAVAILABLE, ReleaseIndex, build_group_index, to_response  # noqa: E402

OUT = ROOT / "android" / "contract-fixtures" / "librarian"
CAPTURED_AT = "2026-11-10T00:00:00Z"
RG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
R_US = "11111111-1111-4111-8111-111111111111"   # 1958 US LP (the owned edition)
R_JP = "22222222-2222-4222-8222-222222222222"   # 1999 Japan CD
R_NODATE = "33333333-3333-4333-8333-333333333333"
FILE = "https://coverartarchive.org/release/{rel}/{id}.jpg"


def img(rel, i, types, *, approved=True, side=1200, comment="", ext="jpg"):
    return {"id": i, "types": types, "approved": approved, "comment": comment, "width": side, "height": side,
            "image": FILE.format(rel=rel, id=i).replace(".jpg", "." + ext)}


def release(mbid, date, country, fmt):
    return {"id": mbid, "date": date, "country": country, "media": [{"format": fmt}] if fmt else []}


class Fetchers:
    def __init__(self, releases, answers):
        self.releases, self.answers = releases, answers

    def fetch_releases(self, rgid):
        return self.releases

    def fetch_release_index(self, rel):
        return self.answers.get(rel, ReleaseIndex(UNAVAILABLE))

    def fetch_image(self, *args, **kwargs):
        return ("unavailable", b"", "")


SCENARIOS = {
    "ok": Fetchers(
        [release(R_US, "1958-08-18", "US", "Vinyl"), release(R_JP, "1999-05-01", "JP", "CD"),
         release(R_NODATE, "", "", "")],
        {R_US: ReleaseIndex(OK, (img(R_US, 1001, ["Front"]), img(R_US, 1002, ["Back"]),
                                 img(R_US, 1003, ["Medium"], comment="Side A label"))),
         R_JP: ReleaseIndex(OK, (img(R_JP, 1001, ["Front"]), img(R_JP, 2001, ["Front"], side=1500),
                                 img(R_JP, 2002, ["Booklet"], comment="Page 1"),
                                 img(R_JP, 2003, ["Booklet"], comment="Page 2"),
                                 img(R_JP, 2004, ["Obi"], approved=False),
                                 img(R_JP, 2005, ["Booklet"], comment="Booklet scan (PDF)", ext="pdf"))),
         R_NODATE: ReleaseIndex(EMPTY)}),
    "empty": Fetchers([release(R_US, "1958-08-18", "US", "Vinyl")], {R_US: ReleaseIndex(EMPTY)}),
    "unavailable": Fetchers(None, {}),
    # one release's index failed: the rest is served and flagged, never counted as empty
    "truncated": Fetchers(
        [release(R_US, "1958-08-18", "US", "Vinyl"), release(R_JP, "1999-05-01", "JP", "CD")],
        {R_US: ReleaseIndex(OK, (img(R_US, 1001, ["Front"]), img(R_US, 1002, ["Back"]))),
         R_JP: ReleaseIndex(UNAVAILABLE)}),
}


@contextlib.contextmanager
def small_caps(**caps):
    """Lower the real caps (releases_cap, served_cap, time_bound) so a tiny body shows each truncation reason.

    The values in these fixtures are therefore not the production caps (60 releases, 250 served, 180 s)."""
    targets = {"releases_cap": build_group_index, "time_bound": build_group_index, "served_cap": to_response}
    saved = {k: targets[k].__kwdefaults__[k] for k in caps}
    for k, v in caps.items():
        targets[k].__kwdefaults__[k] = v
    try:
        yield
    finally:
        for k, v in saved.items():
            targets[k].__kwdefaults__[k] = v


def record(name: str, params: dict, fetchers: Fetchers | None, *, build: bool, warm=()) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        service = ArtworkService(ArtworkStore(Path(tmp)), fetchers)
        if warm:        # an earlier build already read these releases, so this one only resumes
            service.store.put_group(RG, [_trim_doc(d) for d in fetchers.releases], params.get("release"), "partial", 1)
            for rel in warm:
                service.store.put_release(rel, fetchers.answers[rel])
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[routes.get_service] = lambda: service
        try:
            if build:
                service.build_now(RG, params.get("release"))
            res = TestClient(api).get("/api/artwork/index", params=params)
        finally:
            service._pool.shutdown()
    return {"captured_at": CAPTURED_AT,
            "request": {"body": None, "method": "GET", "path": "/api/artwork/index", "query": params},
            "response": {"body": res.json(), "content_type": res.headers["content-type"],
                         "elapsed_seconds": 0.0, "status": res.status_code}}


def all_fixtures() -> dict[str, dict]:
    own = {"rgid": RG, "release": R_US}
    out = {f"artwork_index{'' if k == 'ok' else '_' + k}.json": record(k, own, f, build=True)
           for k, f in SCENARIOS.items()}
    two = SCENARIOS["ok"]
    with small_caps(releases_cap=2):          # 3 releases, cap 2: the undated one is never read
        out["artwork_index_truncated_release_cap.json"] = record("rc", own, two, build=True)
    with small_caps(served_cap=3):            # 8 images, 3 served: slot winners first
        out["artwork_index_truncated_served_cap.json"] = record("sc", own, two, build=True)
    # No `time` fixture: the route rebuilds from the per-release cache, where an unread release counts as
    # failed, so a time-bounded build is served as `partial` (see docs/artwork.md, contract section).
    out["artwork_index_not_loaded.json"] = record("not_loaded", {"rgid": RG}, SCENARIOS["ok"], build=False)
    out["artwork_index_error_bad_rgid.json"] = record("bad", {"rgid": "not-an-id"}, SCENARIOS["ok"], build=False)
    return out


def main() -> None:
    for name, doc in all_fixtures().items():
        (OUT / name).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(name, doc["response"]["status"], doc["response"]["body"].get("status"))


if __name__ == "__main__":
    main()
