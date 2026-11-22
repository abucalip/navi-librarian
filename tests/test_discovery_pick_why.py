"""Direct-import tests for discovery.pick_why (Listening Room L0, D1 = server)."""
import unittest

from discovery.pick_why import attach_why, build_pick_why


class PickWhyTests(unittest.TestCase):
    def test_r1_bridge_label_wins_over_everything(self):
        why = build_pick_why({
            "bridge_label": "Discover more Broadcast",
            "because": {"kind": "tag", "names": ["electronic"]},
            "similar_to": ["Stereolab"],
            "lens": "deep_cuts",
            "seed_tag": "electronic",
            "owned": True,
        })
        self.assertEqual(why, {
            "kind": "bridge",
            "sentence": "Discover more Broadcast",
            "chips": [],
        })

    def test_r2_because_tag_and_name_joining(self):
        why_one = build_pick_why({"because": {"kind": "tag", "names": ["shoegaze"]}})
        self.assertEqual(why_one["kind"], "tag")
        self.assertEqual(why_one["sentence"], "Because you listen to shoegaze")
        self.assertEqual(why_one["chips"], [
            {"type": "tag", "label": "shoegaze", "value": "shoegaze", "href_kind": "genre"},
        ])

        why_two = build_pick_why({"because": {"kind": "tag", "names": ["shoegaze", "dream pop"]}})
        self.assertEqual(why_two["sentence"], "Because you listen to shoegaze and dream pop")

        why_three = build_pick_why({"because": {"kind": "tag", "names": ["shoegaze", "dream pop", "noise pop"]}})
        self.assertEqual(why_three["sentence"], "Because you listen to shoegaze, dream pop and 1 more")
        self.assertEqual(len(why_three["chips"]), 3)

    def test_r3_because_similar_artists_caps_chips_at_two_plus_more(self):
        why = build_pick_why({
            "because": {"kind": "similar_artists", "names": ["Low", "Grouper", "Codeine", "Duster"]},
            "similar_to": ["Ignored"],
        })
        self.assertEqual(why["kind"], "similar_artists")
        self.assertEqual(why["sentence"], "Shares genres with Low, Grouper and 2 more")
        self.assertEqual(why["chips"], [
            {"type": "artist", "label": "Low", "value": "Low", "href_kind": "artist"},
            {"type": "artist", "label": "Grouper", "value": "Grouper", "href_kind": "artist"},
            {"type": "more", "label": "+2", "value": 2, "href_kind": None},
        ])

    def test_r4_similar_to_fallback(self):
        why = build_pick_why({"similar_to": ["Talk Talk", "Bark Psychosis"]})
        self.assertEqual(why["kind"], "similar_artists")
        self.assertEqual(why["sentence"], "Shares genres with Talk Talk and Bark Psychosis")
        self.assertEqual(len(why["chips"]), 2)

    def test_r5_lens_with_seed_tag_all_five_lenses_and_chips(self):
        cases = {
            "deep_cuts": "A lesser-known record from the jazz you play",
            "current_tastes": "Close to the jazz you play lately",
            "genre_spread": "Through the jazz you play",
            "repeated_tracks": "From the jazz you keep repeating",
            "obsessions": "From your jazz obsession",
        }
        for lens, expected in cases.items():
            why = build_pick_why({
                "lens": lens,
                "seed_tag": "jazz",
                "album_listeners": 41200,
                "tags": ["jazz", "modal jazz", "post-bop", "avant-garde"],
            })
            self.assertEqual(why["kind"], "lens")
            self.assertEqual(why["sentence"], expected)
            self.assertEqual(why["chips"], [
                {"type": "tag", "label": "jazz", "value": "jazz", "href_kind": "genre"},
                {"type": "listeners", "label": "41k listeners", "value": 41200, "href_kind": None},
                {"type": "tag", "label": "modal jazz", "value": "modal jazz", "href_kind": "genre"},
                {"type": "tag", "label": "post-bop", "value": "post-bop", "href_kind": "genre"},
            ])

    def test_r6_lens_without_seed_tag_and_dashboard_pick(self):
        why = build_pick_why({"lens": "repeated_tracks", "album_listeners": 9600})
        self.assertEqual(why, {
            "kind": "lens",
            "sentence": "From your Repeated tracks lens",
            "chips": [{"type": "listeners", "label": "9.6k listeners", "value": 9600, "href_kind": None}],
        })

        dash = build_pick_why({
            "dashboard_category": "Current tastes",
            "reason": "From your current tastes: ambient",
            "lastfm_listeners": 1_200_000,
        })
        self.assertEqual(dash, {
            "kind": "lens",
            "sentence": "From your current tastes: ambient",
            "chips": [{"type": "listeners", "label": "1.2M listeners", "value": 1_200_000, "href_kind": None}],
        })

    def test_r7_deep_dive_missing_album_never_uses_internal_reason(self):
        why = build_pick_why({
            "artist": "Stereolab",
            "anchor_artist": "Stereolab",
            "anchor_album_count": 5,
            "deep_dive_kind": "missing_album",
            "reason": "An additional resolved candidate for an artist with at least three albums...",
        })
        self.assertEqual(why, {
            "kind": "deep_dive_missing",
            "sentence": "You have 5 albums by Stereolab. This one is not in your library yet.",
            "chips": [{"type": "library_count", "label": "5 in your library", "value": 5, "href_kind": None}],
        })

    def test_r8_deep_dive_similar_artist(self):
        why = build_pick_why({
            "artist": "Broadcast",
            "anchor_artist": "Stereolab",
            "anchor_album_count": 5,
            "deep_dive_kind": "similar_artist",
        })
        self.assertEqual(why, {
            "kind": "deep_dive_similar",
            "sentence": "Close to Stereolab, who is well covered in your library. Nothing by this artist yet.",
            "chips": [{"type": "artist", "label": "Close to Stereolab", "value": "Stereolab", "href_kind": "artist"}],
        })

    def test_r9_new_release(self):
        why = build_pick_why({
            "year": 2026,
            "artist_library_album_count": 1,
        }, list_name="new_releases")
        self.assertEqual(why, {
            "kind": "new_release",
            "sentence": "New in 2026 from an artist with a full album in your library",
            "chips": [{"type": "library_count", "label": "1 album in your library", "value": 1, "href_kind": None}],
        })

    def test_r10_collection_classics(self):
        why = build_pick_why({
            "artist_library_album_count": 4,
            "lastfm_listeners": 850,
        }, list_name="classics")
        self.assertEqual(why, {
            "kind": "collection",
            "sentence": "A well-known album; you have 4 albums by this artist",
            "chips": [{"type": "listeners", "label": "850 listeners", "value": 850, "href_kind": None}],
        })

    def test_r11_discover_music_categories(self):
        adj = build_pick_why({"discovery_category": "adjacent", "lastfm_listeners": 25_000})
        self.assertEqual(adj["kind"], "discover")
        self.assertEqual(adj["sentence"], "Close to genres you already love")

        cross = build_pick_why({
            "discovery_category": "cross_genre",
            "genre_families": ["jazz", "electronic"],
            "anchor_artist": "Floating Points",
        })
        self.assertEqual(cross["sentence"], "A bridge between jazz and electronic, both in your listening")
        self.assertEqual(cross["chips"], [
            {"type": "artist", "label": "Similar to Floating Points", "value": "Floating Points", "href_kind": "artist"},
        ])

        adv = build_pick_why({"discovery_category": "adventurous"})
        self.assertEqual(adv["sentence"], "A step away from your usual genres")

        unc = build_pick_why({"discovery_category": "unclassified"})
        self.assertEqual(unc["sentence"], "Few genre tags, so the fit is a guess")

    def test_r12_owned_and_none(self):
        self.assertEqual(build_pick_why({"owned": True}), {
            "kind": "owned",
            "sentence": "In your library",
            "chips": [],
        })
        self.assertIsNone(build_pick_why({"artist": "A", "album": "B"}))

    def test_attach_why_leaves_minimal_items_untouched(self):
        items = [{"artist": "A", "album": "B"}, {"artist": "C", "album": "D", "owned": True}]
        out = attach_why(items)
        self.assertNotIn("why", out[0])
        self.assertEqual(out[1]["why"]["kind"], "owned")
