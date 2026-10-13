import unittest
from discovery_recommendations import artist_identity, deep_dive_genre_families, diversify_classic_candidates, exact_artist_credit_matches, is_album_candidate, is_various_artists, music_key, refresh_exploration_scores, score_classic_candidates

class DiscoveryRecommendationRulesTests(unittest.TestCase):
 def test_normalization_and_artist_identity(self):
  self.assertEqual(music_key("Beyoncé"),music_key("Beyonce"))
  self.assertEqual(artist_identity({"artist_mbid":"abc","primary_artist":"A"}),"mbid:abc")
  self.assertEqual(artist_identity({"primary_artist":"Beyoncé"}),"name:beyonce")
 def test_album_eligibility(self):
  self.assertTrue(is_album_candidate({"album":"Blue Train","primary_type":"Album"}))
  self.assertFalse(is_album_candidate({"album":"Blue Train","primary_type":"EP"}))
  self.assertFalse(is_album_candidate({"album":"Greatest Hits","primary_type":"Album"}))
  self.assertFalse(is_album_candidate({"album":"Album","secondary_types":["Compilation"]}))
  self.assertFalse(is_album_candidate(None))
 def test_exact_credit_and_various_artists(self):
  self.assertTrue(exact_artist_credit_matches([{"artist":{"name":"Queen"}}],"Queen"))
  self.assertFalse(exact_artist_credit_matches([{"artist":{"name":"Queen Tribute"}}],"Queen"))
  self.assertTrue(is_various_artists("V.A.")); self.assertFalse(is_various_artists("The Various"))
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
if __name__=="__main__": unittest.main()
