import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

/// The album Paths sheet's model, from the recorded album fixtures.
@Suite @MainActor struct PathsModelTests {
    private func body(_ name: String, file: String = #filePath) throws -> Data {
        let url = URL(fileURLWithPath: file).deletingLastPathComponent()
            .deletingLastPathComponent().appending(path: "DiscairLibrarianTests/Fixtures/\(name).json")
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
    }

    @Test func tabsHaveOneWordTitles() {
        #expect(AlbumPathTab.available(sonic: true).map(\.label) == ["Crew", "Guests", "Covers", "Scene", "Room", "Gaps", "Sonic"])
    }

    private func story(_ json: String) throws -> String {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8))
        return PathAnswer(album: p).steps[0].story.map { $0.map(\.text).joined() }.joined(separator: "\n")
    }

    private func path(_ reasons: String, owned: Bool = false) -> String {
        #"{"kind":"album_room","status":"ok","start":{"mbid":"s","canonical_name":"Round About Midnight","type":"release","owned":true},"stops":[{"entity":{"mbid":"t","canonical_name":"Bags and Trane","type":"release","owned":\#(owned)},"presentation":{"album_artist":"Milt Jackson"},"reasons":\#(reasons)}]}"#
    }

    @Test func roomStoryListsTheTracksOnceAndNamesTheStopsTrack() throws {
        func r(_ track: String) -> String {
            #"{"code":"recorded_at","text":"x","via":{"mbid":"v","canonical_name":"CBS 30th Street Studio","type":"place"},"anchor":{"mbid":"a","canonical_name":"\#(track)","type":"recording"},"target":{"mbid":"g","canonical_name":"Dead Old Stockholm","type":"recording"}}"#
        }
        let text = try story(path("[" + ["Round Midnight", "All of You", "Tadd's Delight"].map(r).joined(separator: ",") + "]"))
        #expect(text == "CBS 30th Street Studio is where Round Midnight, All of You and Tadd's Delight from Round About Midnight were made (recorded, mixed or engineered) and where Dead Old Stockholm from Bags and Trane was made.")
    }

    @Test func crewStoryAndTheForbiddenWords() throws {
        let one = #"[{"code":"crew_on","text":"x","via":{"mbid":"v","canonical_name":"Rudy van Gelder","type":"artist"},"anchor":{"mbid":"s","canonical_name":"Round About Midnight","type":"release"}}]"#
        let text = try story(path(one))
        #expect(text == "Rudy van Gelder has a production credit on Round About Midnight and on Bags and Trane.")
        for banned in ["this album", "a recording", "started from"] { #expect(!text.contains(banned)) }
    }

    @Test func stopsOutsideTheLibraryAreMarkedNotOwned() throws {
        let one = #"[{"code":"crew_on","text":"x","via":{"mbid":"v","canonical_name":"R","type":"artist"},"anchor":{"mbid":"s","canonical_name":"Round About Midnight","type":"release"}}]"#
        let a = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: Data(path(one).utf8)))
        #expect(a.steps[0].owned == false)
        let b = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: Data(path(one, owned: true).utf8)))
        #expect(b.steps[0].owned)
    }

    @Test func neighboursByEarIsOfferedOnlyWithSonic() {
        #expect(!AlbumPathTab.available(sonic: false).contains(.neighboursByEar))
        #expect(AlbumPathTab.available(sonic: true).count == 7)
        #expect(AlbumPathTab.available(sonic: false).count == 6)
    }

    @Test func graphStepsKeepServerOrderAndNameThePerson() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_crew"))
        let a = PathAnswer(album: p)
        #expect(a.steps.map(\.name) == p.stops.map(\.entity.name))
        #expect(a.steps.first?.detail == "Cannonball Adderley")
        #expect(a.steps.first?.why == "Rudy van Gelder")
        #expect(a.steps.allSatisfy { !$0.reasons.isEmpty })
    }

    @Test func sameRoomNamesThePlace() throws {
        let a = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_room")))
        #expect(a.steps.first?.why == "Van Gelder Studio")
        #expect(a.steps.first?.reasons.first?.eyebrow == "Recorded at")
    }

    @Test func gapsShowThePlayLabelInServerOrder() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_gaps"))
        let a = PathAnswer(album: p)
        #expect(a.steps.map(\.name) == p.stops.map(\.entity.name))
        #expect(a.steps.first?.why == "Not played" && a.steps.first?.play == "Not played")
        #expect(a.notes.isEmpty)
    }

    @Test func gapsWithUnavailableHistorySayEveryAlbumIsListed() throws {
        let a = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_gaps_unavailable")))
        #expect(!a.steps.isEmpty && a.steps.allSatisfy { $0.play == nil })
        #expect(a.notes.count == 1 && a.notes[0].contains("could not be read") && a.notes[0].contains("played or not"))
        #expect(PathAnswer.historyNotes(PathHistory(state: "thin", playedAlbums: 5, filteredOut: 0, unknown: 0, littlePlaysBelow: 2))[0].contains("too short"))
    }

    @Test func gapsEmptyBecauseEverythingWasPlayedSaysSo() throws {
        let a = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_gaps_empty")))
        #expect(a.steps.isEmpty)
        #expect(a.empty?.hasPrefix("Every album these credits reach is one you have already played") == true)
        let m = PathsSheetModel(albumTitle: "A", artist: "B", albumID: "1", sonicAvailable: false)
        m.choose("listenThroughGaps")
        #expect(m.emptyText == "No Listen-through Gaps path from A yet. A path appears only when every step has evidence.")
    }

    @Test func emptyAnswerStatesTheRule() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: body("paths_album_guests_empty"))
        #expect(PathAnswer(album: p).steps.isEmpty)
        let m = PathsSheetModel(albumTitle: "A", artist: "B", albumID: "1", sonicAvailable: false)
        m.choose("guestList")
        #expect(m.emptyText == "No Guest List path from A yet. A path appears only when every step has evidence.")
    }

    @Test func neighboursShowMatchedTrackCountAndSkippedSeeds() throws {
        let n = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: body("sonic_album_neighbours"))
        let a = PathAnswer(album: n)
        #expect(a.seeds == 4 && a.steps.first?.why == "4 of 4 tracks")
        let e = try JSONDecoder().decode(SonicAlbumNeighbours.self, from: body("sonic_album_neighbours_empty"))
        #expect(PathAnswer(album: e).notes == ["1 track has no sound analysis and was skipped."])
    }

    @Test func cappedIsSaidInWords() throws {
        let json = #"{"kind":"album_crew","status":"ok","start":{"mbid":"m","canonical_name":"X","type":"release","owned":true},"capped":[{"via":"Rudy van Gelder","more":12},{"via":"Al","more":1}],"truncated":"time","stops":[]}"#
        let a = PathAnswer(album: try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8)))
        #expect(a.notes == ["12 more albums with Rudy van Gelder are not shown.", "1 more album with Al is not shown.",
                            "The server stopped this path early (time limit), so later steps may be missing."])
    }

    @Test func moveStaysInsideTheList() throws {
        let m = PathsSheetModel(albumTitle: "A", artist: "B", albumID: "1", sonicAvailable: false)
        #expect(m.tabID == "studioCrew" && m.selected == nil)
        m.move(by: 1)
        #expect(m.selected == nil)
    }

    @Test func artistPathsHaveFiveTabsWithAndroidWording() {
        let m = PathsSheetModel(artistName: "Miles Davis") { "mbid" }
        #expect(m.tabLabels.map(\.label) == ["Follow the Musician", "Sideman", "Label", "Composition", "Scene"])
        #expect(m.summary == "Songs, not in your library, by musicians who also played with Miles Davis.")
        #expect(PathKind.sidemanToLeader.summary(artist: "X", startType: "group") == "Artists whose records X appeared on as guests.")
        #expect(PathKind.sidemanToLeader.summary(artist: "X", startType: "person") == "Artists whose records X played on as a sideman.")
        #expect(m.heading == "Paths from Miles Davis")
    }

    @Test func artistLabelStepsAreAlbumsAndSidemanStepsAreArtists() throws {
        let json = #"""
        {"kind":"label_path","status":"ok","start":{"mbid":"m","canonical_name":"X","type":"person","owned":true},
         "stops":[{"entity":{"mbid":"a","canonical_name":"Time Further Out","type":"release","owned":true},
                   "presentation":{"album_artist":"The Dave Brubeck Quartet"},
                   "reasons":[{"code":"same_label","text":"Columbia","via":{"mbid":"l","canonical_name":"Columbia","type":"label","owned":false},"evidence":[]}]}]}
        """#
        let a = PathAnswer(artist: try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8)), kind: .labelPath)
        #expect(a.steps.first?.target == .album(title: "Time Further Out", artist: "The Dave Brubeck Quartet", albumID: nil))
        #expect(a.steps.first?.detail == "The Dave Brubeck Quartet" && a.steps.first?.why == "Columbia")
        let s = PathAnswer(artist: try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8)), kind: .scenePath)
        #expect(s.steps.first?.target == .artist(name: "Time Further Out") && s.steps.first?.detail == "Artist")
    }
}
