import AppKit
import DiscairCore
import DiscairNavidrome
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private func decode<T: Decodable>(_ type: T.Type, _ json: String) throws -> T {
    try JSONDecoder().decode(T.self, from: Data(json.utf8))
}

private let newest = #"[{"id":"al-1","name":"Laughing Stock","artist":"Talk Talk","artistId":"ar-1","coverArt":"al-1","songCount":6,"duration":2460,"year":1991,"genre":"Post-rock"},{"id":"al-2","name":"Dummy","artist":"Portishead","artistId":"ar-2","year":1994}]"#
private let artistsJSON = #"[{"id":"ar-1","name":"Talk Talk","albumCount":3},{"id":"ar-2","name":"Portishead","albumCount":1},{"id":"ar-3","name":"Árbol","albumCount":2},{"id":"ar-4","name":"10cc","albumCount":1}]"#
private let picksJSON = #"{"items":[{"artist":"Can","album":"Tago Mago","reason":"A double album you have never owned.","genres":["krautrock"],"suggested_tracks":["Halleluhwah","Paperhouse"]},{"artist":"Talk Talk","album":"Laughing Stock","reason":"already owned"},{"artist":"Talk Talk","album":"The Colour of Spring"}]}"#

@MainActor
struct LibraryModelTests {
    @Test func startsWithSampleData() {
        let m = LibraryModel()
        #expect(m.phase == .sample && !m.isLive)
        #expect(m.missing.first?.title == "Tago Mago")
        #expect(m.tracks.count == Fixtures.tracks.count)
    }

    @Test func appliesLiveDataAndDropsOwnedPicks() throws {
        let m = LibraryModel()
        m.apply(newest: try decode([NavidromeAlbum].self, newest), first: try decode([NavidromeAlbum].self, newest),
                artists: try decode([NavidromeArtist].self, artistsJSON), picks: try decode(DashboardPicks.self, picksJSON).items)
        #expect(m.phase == .loaded && m.isLive)
        #expect(m.recent.map(\.title) == ["Laughing Stock", "Dummy"])
        #expect(m.recent[0].remoteID == "al-1" && m.recent[0].coverArt == "al-1" && m.recent[0].owned)
        #expect(m.missing.map(\.title) == ["Tago Mago", "The Colour of Spring"])   // the owned pick is removed
        #expect(m.missing[0].reason == "A double album you have never owned." && m.missing[0].suggestedTracks == ["Halleluhwah", "Paperhouse"])
        #expect(!m.missing[0].owned && m.missing[0].remoteID == nil)
        #expect(m.totalAlbumsText == "Library 7 albums")
    }

    @Test func saysWhyThereAreNoRecommendations() throws {
        let m = LibraryModel()
        let albums = try decode([NavidromeAlbum].self, newest)
        m.apply(newest: albums, first: albums, artists: [], picks: [], picksNote: "Add your Librarian login in Settings to see recommendations.")
        #expect(m.missing.isEmpty && m.picksNote?.contains("Settings") == true)
        m.apply(newest: albums, first: albums, artists: [], picks: [])
        #expect(m.picksNote == "The Librarian has no recommendations for you right now.")
        m.apply(newest: albums, first: albums, artists: [], picks: try decode(DashboardPicks.self, picksJSON).items)
        #expect(m.picksNote == nil && !m.missing.isEmpty)
    }

    @Test func artistLettersFoldAccentsAndNumbers() throws {
        let m = LibraryModel()
        m.apply(newest: [], first: [], artists: try decode([NavidromeArtist].self, artistsJSON), picks: [])
        #expect(m.artists.map(\.letter) == ["T", "P", "A", "#"])
    }

    @Test func placeholderHueIsStable() {
        #expect(LibraryModel.hue(for: "Dummy") == LibraryModel.hue(for: "dummy"))
        #expect((0..<360).contains(LibraryModel.hue(for: "Dummy")))
    }

    @Test func tracksShowDurationAndQuality() throws {
        let songs = try decode([NavidromeSong].self, #"[{"id":"s1","title":"Myrrhman","duration":412,"suffix":"flac","bitRate":1546},{"id":"s2","title":"Taphead","duration":65,"suffix":"mp3","bitRate":320},{"id":"s3","title":"Odd"}]"#)
        let t = LibraryModel.tracks(songs)
        #expect(t.map(\.duration) == ["6:52", "1:05", ""])
        #expect(t.map(\.format) == ["FLAC", "MP3 320", ""])
        #expect(t.allSatisfy { $0.owned })
    }

    @Test func aPickShowsSuggestedTracksAsNotOwned() async throws {
        let m = LibraryModel()
        m.apply(newest: [], first: [], artists: [], picks: try decode(DashboardPicks.self, picksJSON).items)
        await m.loadTracks(for: m.missing[0], navidrome: nil)
        #expect(m.tracks.map(\.title) == ["Halleluhwah", "Paperhouse"])
        #expect(m.tracks.allSatisfy { !$0.owned })
    }

    @Test func artistPageListsPicksByThatArtistAsMissing() async throws {
        let m = LibraryModel()
        let artists = try decode([NavidromeArtist].self, artistsJSON)
        m.apply(newest: [], first: [], artists: artists, picks: try decode(DashboardPicks.self, picksJSON).items)
        await m.loadArtist(m.artists[0], navidrome: nil)
        // No owned albums were loaded here, so both picks by Talk Talk count as missing.
        #expect(m.artistAlbums.map(\.title) == ["Laughing Stock", "The Colour of Spring"])
        #expect(m.artistMissingCount == 2 && m.artistOwnedCount == 0)
    }

    @Test func moreByArtistSkipsTheAlbumItself() throws {
        let m = LibraryModel()
        let list = try decode([NavidromeAlbum].self, #"[{"id":"a","name":"One","artist":"X"},{"id":"b","name":"Two","artist":"X"},{"id":"c","name":"Three","artist":"Y"}]"#)
        m.apply(newest: list, first: list, artists: [], picks: [])
        #expect(m.more(by: m.recent[0]).map(\.title) == ["Two"])
    }
}

private struct CountingTransport: HTTPTransport {
    let counter: Counter
    let status: Int
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        counter.hit(request.url!)
        let png = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 4, pixelsHigh: 4, bitsPerSample: 8, samplesPerPixel: 4,
                                   hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        let data = status == 200 ? png.representation(using: .png, properties: [:])! : Data()
        return (data, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

final class Counter: @unchecked Sendable {
    private let lock = NSLock(); private var urls: [URL] = []
    func hit(_ u: URL) { lock.withLock { urls.append(u) } }
    var all: [URL] { lock.withLock { urls } }
}

@MainActor
struct ArtworkStoreTests {
    private func builder() throws -> StreamURLBuilder {
        try StreamURLBuilder(baseURL: URL(string: "http://192.168.1.87:4533")!,
                             auth: SubsonicAuth(credential: Credential(username: "owner", password: "pw")))
    }

    @Test func fetchesOnceAndCaches() async throws {
        let counter = Counter()
        let store = ArtworkStore(transport: CountingTransport(counter: counter, status: 200))
        store.configure(try builder())
        let a = await store.image(coverArt: "al-1", px: 300)
        let b = await store.image(coverArt: "al-1", px: 300)
        #expect(a != nil && b != nil)
        #expect(counter.all.count == 1)
        #expect(counter.all[0].path.hasSuffix("/rest/getCoverArt"))
        _ = await store.image(coverArt: "al-1", px: 600)   // a different size is a different request
        #expect(counter.all.count == 2)
    }

    @Test func doesNothingWithoutAProfileAndRemembersFailures() async throws {
        let counter = Counter()
        let store = ArtworkStore(transport: CountingTransport(counter: counter, status: 404))
        #expect(await store.image(coverArt: "al-1", px: 300) == nil && counter.all.isEmpty)
        store.configure(try builder())
        #expect(await store.image(coverArt: "al-1", px: 300) == nil)
        #expect(await store.image(coverArt: "al-1", px: 300) == nil)
        #expect(counter.all.count == 1)   // the failure is not retried on every redraw
    }

    @Test func refusesAnInvalidCoverID() async throws {
        let counter = Counter()
        let store = ArtworkStore(transport: CountingTransport(counter: counter, status: 200))
        store.configure(try builder())
        #expect(await store.image(coverArt: "../../etc", px: 300) == nil && counter.all.isEmpty)
    }

    // MARK: Songs table

    @Test func aLiveLibraryNeverShowsSampleSongs() throws {
        let m = LibraryModel()
        #expect(m.songs.count == Fixtures.songs.count)
        m.apply(newest: [], first: [], artists: [], picks: [])
        #expect(m.songs.isEmpty)
    }

    @Test func songRowsReadTheServersFields() throws {
        let song = try decode(NavidromeSong.self, #"{"id":"s1","title":"Roygbiv","album":"Music Has the Right to Children","albumId":"al-9","artist":"Boards of Canada","year":1998,"genre":"IDM","coverArt":"mf-1","suffix":"flac","bitRate":900,"bitDepth":16,"samplingRate":44100,"playCount":41,"created":"2020-10-12T13:44:03.224611619Z","played":"2020-10-13T10:00:00Z"}"#)
        let r = LibraryModel.row(song, id: 3)
        #expect(r.remoteID == "s1" && r.title == "Roygbiv" && r.artist == "Boards of Canada" && r.year == 1998 && r.plays == 41)
        #expect(r.format == "FLAC 16/44" && r.bitrate == "900 kb")
        #expect(r.albumItem.remoteID == "al-9" && r.albumItem.coverArt == "mf-1")
        #expect(r.added.hasPrefix("Oct") && r.lastPlayed.hasPrefix("Oct"))
        let mp3 = try decode(NavidromeSong.self, #"{"id":"s2","title":"X","suffix":"mp3","bitRate":320,"bitDepth":0,"samplingRate":44100}"#)
        #expect(LibraryModel.row(mp3, id: 0).format == "MP3 320" && LibraryModel.row(mp3, id: 0).plays == 0)
    }

    @Test func dateWordsAreRelativeToNow() {
        let now = ISO8601DateFormatter().date(from: "2026-11-04T12:00:00Z")!
        #expect(LibraryModel.shortDate("2026-11-04T08:00:00Z", now: now) == "Today")
        #expect(LibraryModel.shortDate("2026-11-03T12:00:00Z", now: now) == "Yesterday")
        #expect(LibraryModel.shortDate(nil, now: now) == "" && LibraryModel.shortDate("0001-01-01T00:00:00Z", now: now) == "")
    }
}

