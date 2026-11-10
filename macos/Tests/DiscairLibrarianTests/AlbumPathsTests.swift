import Foundation
import Testing
@testable import DiscairLibrarian

/// Album paths (`type=release`) and album sonic neighbours: the recorded payloads decode into what the page shows.
@Suite struct AlbumPathsTests {
    /// The `response.body` of a recorded fixture, as JSON data.
    private func body(_ name: String, file: String = #filePath) throws -> Data {
        let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "Fixtures/\(name).json")
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
    }

    @Test func exactlyTheSixGraphAlbumKindsAreOffered() {
        #expect(AlbumPathKind.allCases.map(\.rawValue) == ["album_crew", "album_guests", "album_works", "album_moment", "album_room", "album_gaps"])
    }

    @Test func gapsFixtureReadsPlayLabelsAndHistory() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_gaps"))
        #expect(p.stops.allSatisfy { $0.play == "Not played" || $0.play?.hasPrefix("Played") == true })
        #expect(p.history == PathHistory(state: "ok", playedAlbums: 274, filteredOut: 0, unknown: 0, littlePlaysBelow: 2))
        let u = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_gaps_unavailable"))
        #expect(u.history?.state == "unavailable" && u.history?.playedAlbums == nil)
        #expect(!u.stops.isEmpty && u.stops.allSatisfy { $0.play == nil })
        let r = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_room"))
        #expect(r.history == nil)
    }

    @Test func okAlbumFixturesListStepsWithReasonsAndOwnedAlbums() throws {
        for kind in AlbumPathKind.allCases {
            let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_\(kind.rawValue)"))
            #expect(p.kind == kind.rawValue && p.status == "ok")
            #expect(!p.stops.isEmpty)
            for stop in p.stops {
                #expect(stop.entity.owned)
                #expect(!stop.reasons.isEmpty && stop.reasons.allSatisfy { !$0.text.isEmpty && !$0.code.isEmpty })
            }
        }
    }

    @Test func emptyAlbumFixturesHaveNoStops() throws {
        for kind in AlbumPathKind.allCases {
            let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_\(kind.rawValue)_empty"))
            #expect(p.status == "empty" && p.stops.isEmpty)
        }
    }

    @Test func crewFixtureHasNoOverlapOrCap() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_crew"))
        #expect(p.overlapDropped == 0 && p.capped.isEmpty)
    }

    @Test func overlapAndCappedAreReadWhenSent() throws {
        let json = """
        {"kind":"album_crew","status":"ok","overlap_dropped":3,"truncated":null,
         "start":{"canonical_name":"S","mbid":"m","owned":true,"type":"release"},
         "capped":[{"via":"Rudy van Gelder","more":12},{"via":{"canonical_name":"Ron Carter","type":"person"},"more":4},
                   {"via":"Nobody","more":0},{"more":2},{"via":"Bad count","more":"x"}],
         "stops":[{"entity":{"canonical_name":"X","mbid":null,"owned":true,"type":"release"},"reasons":[{"code":"crew_on","text":"t"}]}]}
        """
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8))
        #expect(p.overlapDropped == 3)
        #expect(p.capped.map { "\($0.via)|\($0.more)" } == ["Rudy van Gelder|12", "Ron Carter|4"])
        #expect(p.stops.count == 1)
    }

    @Test func albumNotBuiltBodyHasNoStops() throws {
        let p = try? JSONDecoder().decode(KnowledgePaths.self, from: body("paths_error_album_room_not_built"))
        #expect(p == nil || p?.stops.isEmpty == true)
    }

    @Test func sonicAlbumNeighboursOkFixtureKeepsStartSeedsAndMatches() throws {
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: body("sonic_album_neighbours"))
        #expect(n.status == "ok")
        #expect(n.start?.albumID == "55o30LbumfEMwDlKctbZpI" && n.start?.album == "100% Arabica")
        #expect(n.seeds.count == 4 && n.skipped.isEmpty)
        #expect(n.stops.count == 14)
        let first = try #require(n.stops.first)
        #expect(first.album == "Yalil" && first.matchCount == 4 && first.owned)
        #expect(first.reasonText == "Sounds like 4 of this album's tracks")
        #expect(n.truncated == nil)
    }

    @Test func sonicAlbumNeighboursEmptyFixtureReportsTheSkippedSeed() throws {
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: body("sonic_album_neighbours_empty"))
        #expect(n.status == "empty" && n.stops.isEmpty && n.seeds.isEmpty)
        #expect(n.skipped.count == 1 && n.skipped[0].reason == "no_analysis" && n.skipped[0].title == "Love Me")
    }

    @Test func sonicAlbumNeighboursNotFoundBodyIsEmpty() throws {
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: body("sonic_album_neighbours_error_not_found"))
        #expect(n.status == "" && n.stops.isEmpty && n.start == nil)
    }

    @Test func sonicAlbumNeighboursKeepsTheServerOrderNotSimilarity() throws {
        let json = """
        {"status":"ok","stops":[
          {"album":"A","album_id":"a","owned":true,"match_count":1,"similarity":0.1,"reasons":[{"text":"x"}]},
          {"album":"B","album_id":"b","owned":true,"match_count":5,"similarity":0.99,"reasons":[{"text":"y"}]}]}
        """
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: Data(json.utf8))
        #expect(n.stops.map(\.album) == ["A", "B"])
    }

    @Test func sonicAlbumNeighboursLeavesOutStopsWithoutAnID() throws {
        let json = """
        {"status":"ok","stops":[{"album":"No id"},{"album":"Keep","album_id":"k","owned":true}]}
        """
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: Data(json.utf8))
        #expect(n.stops.map(\.album) == ["Keep"])
    }
}
