import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
struct MillerColumnsTests {
    private func row(_ id: Int, _ title: String, artist: String = "A", genre: String = "Rock", album: String = "X",
                     track: Int? = nil, disc: Int? = nil) -> SongRow {
        var r = SongRow(id: id, album: 0, title: title, artist: artist, genre: genre, format: "", bitrate: "", lastPlayed: "", added: "", year: 0, plays: 0)
        r.cover = AlbumItem(id: id, title: album, artist: artist, year: 0, genre: genre, format: "", owned: true, hue: 0)
        r.track = track; r.disc = disc
        return r
    }

    @Test func genresCountSongsAndSortIgnoringCase() {
        let rows = [row(0, "a", genre: "rock"), row(1, "b", genre: "Jazz"), row(2, "c", genre: "rock")]
        #expect(MillerColumns.genres(rows) == [.init(name: "Jazz", count: 1), .init(name: "rock", count: 2)])
    }

    @Test func unknownGenreComesLast() {
        let rows = [row(0, "a", genre: ""), row(1, "b", genre: "Zydeco")]
        #expect(MillerColumns.genres(rows).map(\.name) == ["Zydeco", MillerColumns.unknownGenre])
    }

    @Test func eachChoiceNarrowsTheNextColumn() {
        let rows = [row(0, "a", artist: "Talk Talk", genre: "Art rock", album: "Spirit"), row(1, "b", artist: "Kate Bush", genre: "Art pop", album: "Hounds"),
                    row(2, "c", artist: "Talk Talk", genre: "Art rock", album: "Laughing"), row(3, "d", artist: "Can", genre: "Krautrock", album: "Tago")]
        #expect(MillerColumns.artists(rows, genre: "Art rock").map(\.name) == ["Talk Talk"])
        #expect(MillerColumns.artists(rows, genre: nil).count == 3)
        #expect(MillerColumns.albums(rows, genre: "Art rock", artist: "Talk Talk").map(\.name) == ["Laughing", "Spirit"])
        #expect(MillerColumns.tracks(rows, genre: nil, artist: "Talk Talk", album: "Spirit").map(\.title) == ["a"])
    }

    @Test func tracksFollowDiscThenTrackNumberAndUnnumberedLast() {
        let rows = [row(0, "z", track: 1, disc: 2), row(1, "loose"), row(2, "b", track: 2, disc: 1), row(3, "a", track: 1, disc: 1)]
        #expect(MillerColumns.tracks(rows, genre: nil, artist: nil, album: nil).map(\.title) == ["a", "b", "loose", "z"])
    }

    @Test func aChoiceThatNoLongerExistsIsCleared() {
        let list = [MillerColumns.Entry(name: "Jazz", count: 1)]
        #expect(MillerColumns.valid("Jazz", in: list) == "Jazz")
        #expect(MillerColumns.valid("Rock", in: list) == nil)
        #expect(MillerColumns.valid(nil, in: list) == nil)
    }

    @Test func emptyLibraryGivesEmptyColumns() {
        #expect(MillerColumns.genres([]).isEmpty)
        #expect(MillerColumns.tracks([], genre: nil, artist: nil, album: nil).isEmpty)
    }

    @Test func columnsRender() throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: .cupertino, screen: .library)
        state.library.showSongs(Fixtures.songs)
        let host = NSHostingView(rootView: CupertinoMiller(state: state).frame(width: 1100, height: 460).padding(20))
        host.frame = NSRect(x: 0, y: 0, width: 1140, height: 500)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host; window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try png.write(to: dir.appendingPathComponent("cupertino-miller.png"))
    }
}
