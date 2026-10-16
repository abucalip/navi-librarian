import unittest
from discovery_recommendations import artist_identity, classify_diversity_style, deep_dive_genre_families, diversify_classic_candidates, exact_artist_credit_matches, genre_families, is_album_candidate, is_various_artists, music_key, primary_recent_family, recent_style_families, refresh_exploration_scores, score_classic_candidates

class DiscoveryRecommendationRulesTests(unittest.TestCase):
 def test_normalization_and_artist_identity(self):
  self.assertEqual(music_key("Beyoncé"),music_key("Beyonce"))
  self.assertEqual(artist_identity({"artist_mbid":"abc","primary_artist":"A"}),"mbid:abc")
  self.assertEqual(artist_identity({"primary_artist":"Beyoncé"}),"name:beyonce")
 def test_album_eligibility(self):
  self.assertTrue(is_album_candidate({"album":"Blue Train","primary_type":"Album"}))
  self.assertFalse(is_album_candidate({"album":"Blue Train","primary_type":"EP"}))
  self.assertFalse(is_album_candidate({"album":"Greatest Hits","primary_type":"Album"}))
  self.assertFalse(is_album_candidate({"album":"The Remixes"}))
  self.assertFalse(is_album_candidate({"album":"Live at Wembley"}))
  self.assertFalse(is_album_candidate({"album":"An Ordinary Title","primary_type":"EP"}))
  self.assertFalse(is_album_candidate({"album":"Album","secondary_types":["Compilation"]}))
  self.assertFalse(is_album_candidate(None))
 def test_exact_credit_and_various_artists(self):
  self.assertTrue(exact_artist_credit_matches([{"artist":{"name":"Queen"}}],"Queen"))
  self.assertFalse(exact_artist_credit_matches([{"artist":{"name":"Queen Tribute"}}],"Queen"))
  self.assertFalse(exact_artist_credit_matches([{"artist":{"name":"The Queens"}}],"Queen"))
  self.assertFalse(exact_artist_credit_matches([],"Queen"))
  for value in ("Various Artists", "VARIOUS ARTISTS", "Various Artist", "Various", "V.A."):
   self.assertTrue(is_various_artists(value), value)
  self.assertFalse(is_various_artists("The Various"))
 def test_genre_families(self):
  self.assertEqual(deep_dive_genre_families(["Malian desert blues","Bossa Nova","Jazz"]),["jazz","african","brazilian"])
 def test_scoring(self):
  rows=[{"lastfm_listeners":0,"lastfm_playcount":0},{"lastfm_listeners":100000,"lastfm_playcount":500000},{"musicbrainz_rating":4.5,"musicbrainz_rating_votes":20}]
  score_classic_candidates(rows,lambda _a,_b:0)
  self.assertEqual(rows[0]["discovery_score"],0.9); self.assertLess(rows[1]["discovery_score"],rows[0]["discovery_score"])
  self.assertEqual(rows[2]["discovery_score"],1.44)
 def test_jitter_and_diversity(self):
  rows=[{"discovery_score":1.25}]; refresh_exploration_scores(rows,lambda _a,b:b); self.assertEqual(rows[0]["exploration_score"],2.65)
  items=[{"artist":"A","album":f"A{i}","genre_families":["jazz"],"exploration_score":10-i} for i in range(3)]
  items += [{"artist":f"B{i}","album":"B","genre_families":["jazz"],"exploration_score":5-i} for i in range(10)]
  result=diversify_classic_candidates(items,limit=10,per_artist=2,per_family=2)
  self.assertEqual(sum(x["artist"]=="A" for x in result),2); self.assertEqual(len(result),10)
  self.assertEqual(sum(x.get("primary_genre_family")=="jazz" for x in result),2)

 def test_recommendation_genre_families_and_style_families(self):
  self.assertEqual(
   genre_families(["Jazz", "Bossa Nova", "Malian desert blues", "Raï"]),
   {"jazz", "brazilian", "african", "north-african-middle-eastern"},
  )
  self.assertEqual(
   recent_style_families(["Jazz rap", "Bossa Nova", "Raï"]),
   {"hip-hop", "bossa_nova_brazilian", "north_african"},
  )
  self.assertEqual(recent_style_families(["Electronic rock"]), {"electronic"})

 def test_primary_recent_family_prioritizes_specific_style(self):
  self.assertEqual(primary_recent_family(["Jazz rap"], {"jazz": 8, "hip-hop": 2}), "hip-hop")
  self.assertEqual(primary_recent_family(["Afro-jazz"], {"african": 8}), "jazz")
  self.assertIsNone(primary_recent_family([], {}))

 def test_diversity_style_classification_and_overrides(self):
  self.assertEqual(classify_diversity_style({"primary_artist": "Khaled"}, []), "north_african")
  self.assertEqual(classify_diversity_style({"artist": "Tinariwen"}, []), "malian_desert_blues")
  self.assertEqual(classify_diversity_style({"artist": "Unknown"}, ["Afrobeats"]), "afrobeats")
  self.assertEqual(
   classify_diversity_style({"artist": "Unknown", "regional_styles": ["afro_jazz"]}, ["Raï"]),
   "afro_jazz",
  )
  self.assertEqual(classify_diversity_style({"artist": "Unknown"}, ["Indie rock"]), "other")


 def test_deep_dive_ranking_weights_candidate_evidence_and_filters_candidates(self):
  from discovery_recommendations import rank_and_diversify_deep_dive_candidates
  rows = [
   {"artist":"A","album":"Known","lastfm_listeners":1000000,"candidate_pool_score":0.0,
    "anchor_artist":"Anchor","anchor_album_count":5,"genre_families":["jazz"]},
   {"artist":"B","album":"Less Known","lastfm_listeners":10,"candidate_pool_score":2.0,
    "anchor_artist":"Anchor B","anchor_album_count":6,"genre_families":["brazilian"]},
   {"artist":"C","album":"Compilation","lastfm_listeners":10,"candidate_pool_score":0.0,
    "genre_families":["rock"]},
  ]
  ranked, diversified = rank_and_diversify_deep_dive_candidates(
   rows, music_key=music_key, is_album_candidate=is_album_candidate,
   jitter=lambda _low,_high: 0.0, limit=10,
  )
  self.assertEqual([item["album"] for item in ranked], ["Less Known", "Known"])
  self.assertEqual(len(diversified), 2)
  self.assertGreater(ranked[0]["discovery_score"], ranked[1]["discovery_score"])

 def test_deep_dive_diversity_caps_artist_anchor_and_genre(self):
  from discovery_recommendations import rank_and_diversify_deep_dive_candidates
  rows = [
   {"artist":"Same","album":f"Album {i}","lastfm_listeners":0,"anchor_artist":"Anchor",
    "anchor_album_count":3,"genre_families":["jazz"]}
   for i in range(6)
  ]
  rows += [
   {"artist":f"Other {i}","album":"Record","lastfm_listeners":0,"anchor_artist":f"Anchor {i}",
    "anchor_album_count":3,"genre_families":["jazz"]}
   for i in range(14)
  ]
  ranked, diversified = rank_and_diversify_deep_dive_candidates(
   rows, music_key=music_key, is_album_candidate=is_album_candidate,
   jitter=lambda _low,_high: 0.0, limit=150,
  )
  self.assertEqual(len(ranked), 20)
  self.assertLessEqual(sum(item["artist"]=="Same" for item in diversified), 2)
  self.assertLessEqual(sum(item.get("primary_genre_family")=="jazz" for item in diversified), 12)

if __name__=="__main__": unittest.main()
