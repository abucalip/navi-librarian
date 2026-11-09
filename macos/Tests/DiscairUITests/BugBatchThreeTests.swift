import AppKit
import DiscairAudio
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct BugBatchThreeTests {
    @Test func searchIgnoresApostrophesAndPunctuation() {
        #expect(LibrarySearch.matches(["Somethin’ Else", "Cannonball Adderley"], query: "somethin else"))
        #expect(LibrarySearch.matches(["Somethin' Else"], query: "somethin’ else"))
        #expect(LibrarySearch.matches(["AC/DC"], query: "acdc"))
        #expect(LibrarySearch.matches(["Beyoncé"], query: "beyonce"))
        #expect(!LibrarySearch.matches(["Somethin’ Else"], query: "somethin other"))
    }

    @Test func serverSongsFollowLoadedOnesWithoutRepeats() {
        func row(_ id: Int, _ title: String, remote: String) -> SongRow {
            SongRow(id: id, album: 0, title: title, artist: "A", genre: "", format: "", bitrate: "", lastPlayed: "", added: "", year: 0, plays: 0, remoteID: remote)
        }
        let local = [row(1, "Autumn Leaves", remote: "s1")]
        let server = [row(2, "Autumn Leaves", remote: "s1"), row(3, "Autumn Serenade", remote: "s2")]
        let r = LibrarySearch.results(query: "autumn", artists: [], albums: [], songs: local, serverSongs: server)
        #expect(r.songs.compactMap(\.remoteID) == ["s1", "s2"])
    }

    @Test func aSongWithoutItsOwnCoverShowsItsAlbumsCover() {
        let withAlbum = QueueItem(songID: "s", title: "T", artist: "A", albumID: "alb1", coverArt: nil)
        #expect(withAlbum.coverArt == "al-alb1")
        #expect(QueueItem(songID: "s", title: "T", artist: "A", albumID: "alb1", coverArt: "").coverArt == "al-alb1")
        #expect(QueueItem(songID: "s", title: "T", artist: "A", albumID: "alb1", coverArt: "mf-9").coverArt == "mf-9")
        #expect(QueueItem(songID: "s", title: "T", artist: "A").coverArt == nil)
    }

    @Test func theQualityLabelPrefersTheStatedQualityThenTheSuffix() {
        #expect(QueueItem(songID: "s", title: "T", artist: "A", suffix: "flac", quality: "FLAC 16/44").qualityLabel == "FLAC 16/44")
        #expect(QueueItem(songID: "s", title: "T", artist: "A", suffix: "mp3").qualityLabel == "MP3")
        #expect(QueueItem(songID: "s", title: "T", artist: "A").qualityLabel == nil)
    }

    @Test func spaceIsTakenOnlyWhenNothingIsBeingTyped() {
        #expect(SpaceBarPlayPause.shouldHandle(keyCode: 49, modifiers: [], firstResponder: nil))
        #expect(!SpaceBarPlayPause.shouldHandle(keyCode: 49, modifiers: [.command], firstResponder: nil))
        #expect(!SpaceBarPlayPause.shouldHandle(keyCode: 0, modifiers: [], firstResponder: nil))
        #expect(!SpaceBarPlayPause.shouldHandle(keyCode: 49, modifiers: [], firstResponder: NSTextView()))
    }

    @Test func theTimelineKeepsStudioAlbumsOnly() {
        for t in ["Kind of Blue", "Somethin’ Else", "Live at the Fillmore", "Greatest Hits", "The Best of Miles", "Kind of Blue (Deluxe Edition)", "Sessions"] {
            #expect(TimelineGrouping.isStudioTitle(t) == ["Kind of Blue", "Somethin’ Else"].contains(t), "\(t)")
        }
        #expect(TimelineGrouping.isStudioTitle("Alive"))        // "live" inside a word is not a live album
    }

    private func item(_ name: String, type: String? = nil, secondary: [String] = [], kind: String = "album") -> TimelineItem {
        let rt = type.map { #","release_type":{"primary":"\#($0)","secondary":[\#(secondary.map { "\"\($0)\"" }.joined(separator: ","))]}"# } ?? ""
        let json = #"{"kind":"\#(kind)","entity":{"mbid":"\#(name)","canonical_name":"\#(name)","type":"release_group"},"owned":false,"date":"1970","why":"","evidence":[]\#(rt)}"#
        return try! JSONDecoder().decode(TimelineItem.self, from: Data(json.utf8))
    }

    @Test func theServersReleaseTypeDecidesWhatIsAStudioAlbum() {
        let items = [item("A", type: "Album"), item("B", type: "Album", secondary: ["Live"]), item("C", type: "EP"),
                     item("Live Looking", type: "Album"), item("D"), item("Live at X"), item("E", kind: "event")]
        #expect(TimelineGrouping.studioAlbums(items).map(\.entity.name) == ["A", "Live Looking", "D"])
    }

    @Test func anInsightsPageReadsAgainEveryFewMinutes() {
        #expect(InsightsModel.refreshSeconds == 300)
        #expect(InsightsModel().updatedText == nil)
    }
}
