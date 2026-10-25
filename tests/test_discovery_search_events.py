import json
import unittest

from discovery.search.events import search_events, search_partial, sse
from discovery.search.index import IndexView, STATE_BUILDING, STATE_FRESH, STATE_STALE, build_owned_data


def ready_view():
    data = build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Ash", "album_count": 1}],
        albums=[], songs=[],
    )
    return IndexView(STATE_FRESH, data, None)


class SearchEventTests(unittest.TestCase):
    def events(self, view, types=("artist", "album", "song", "genre"), query="ash"):
        return list(search_events(view, query=query, types=types, limit=10, elapsed_ms=lambda: 7))

    def test_invariants_capabilities_first_done_last_exactly_once(self):
        events = self.events(ready_view())
        names = [name for name, _ in events]
        self.assertEqual(names[0], "capabilities")
        self.assertEqual(names[-1], "done")
        self.assertEqual(names.count("done"), 1)
        self.assertNotIn("source", names)
        self.assertNotIn("error", names)

    def test_done_reports_elapsed_and_no_deadline_in_the_owned_only_build(self):
        done = self.events(ready_view())[-1][1]
        self.assertEqual(done, {"elapsed_ms": 7, "deadline_hit": False, "partial": False})

    def test_partial_when_an_owned_type_is_unavailable_with_an_index_reason(self):
        view = IndexView(STATE_BUILDING, None, "index_building")
        self.assertTrue(search_partial(view, ["artist"]))
        self.assertFalse(search_partial(view, ["genre"]))
        self.assertTrue(self.events(view)[-1][1]["partial"])

    def test_stale_index_is_served_and_is_not_partial(self):
        view = IndexView(STATE_STALE, ready_view().data, None)
        self.assertFalse(search_partial(view, ["artist", "album", "song"]))
        capabilities = self.events(view)[0][1]
        self.assertTrue(capabilities["types"]["artist"]["available"])
        self.assertEqual(capabilities["owned_index"]["state"], "stale")

    def test_capabilities_report_genre_and_sources_with_contract_reasons(self):
        capabilities = self.events(ready_view())[0][1]
        self.assertEqual(capabilities["types"]["genre"], {"available": False, "reason": "not_in_this_build"})
        self.assertEqual(capabilities["sources"]["navidrome"], {"available": True, "reason": None})
        self.assertEqual(capabilities["sources"]["discogs"], {"available": False, "reason": "not_in_this_build"})

    def test_read_failure_emits_one_error_and_no_done(self):
        broken = IndexView(STATE_FRESH, object(), None)
        events = self.events(broken)
        self.assertEqual([name for name, _ in events], ["capabilities", "error"])
        error = events[-1][1]
        self.assertEqual(set(error), {"code", "message"})
        self.assertEqual(error["code"], "stream_failed")
        self.assertNotIn("Traceback", error["message"])

    def test_sse_framing_is_one_json_line_per_data_field(self):
        frame = sse("result", {"name": "Beyoncé", "n": 1})
        self.assertEqual(frame, 'event: result\ndata: {"name": "Beyoncé", "n": 1}\n\n')
        self.assertEqual(json.loads(frame.split("data: ", 1)[1]), {"name": "Beyoncé", "n": 1})


if __name__ == "__main__":
    unittest.main()
