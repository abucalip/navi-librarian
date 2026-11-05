import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import DiscairLibrarian
import Testing
@testable import DiscairLibrarian
@testable import DiscairAudio
@testable import DiscairUI

@MainActor
private final class Out: AudioOutput {
    var onFinished: (() -> Void)?
    var onAdvanced: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    var seeks: [Double] = []
    var volume: Float = 1
    func open(file: URL) throws { position = 0 }
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) { seeks.append(seconds); position = seconds }
    func preload(file: URL, transition: Transition) throws {}
    func cancelPreload() {}
    func applyEQ(gains: [Double], preGain: Double) {}
    func setMatchOutputRate(_ on: Bool) {}
    func restoreOutputRate() {}
    func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws { position = 0 }
}

private final class Fetcher: AudioFetcher, @unchecked Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let f = FileManager.default.temporaryDirectory.appending(path: "bug-\(UUID().uuidString).\(suffix ?? "bin")")
        try Data([0]).write(to: f)
        return f
    }
}

private func songs(_ n: Int) -> [QueueItem] {
    (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A", album: "Al", albumID: nil, duration: 200, suffix: "flac", track: $0 + 1, disc: 1) }
}

@MainActor
private func player(_ defaults: UserDefaults) throws -> (PlayerModel, Out) {
    let out = Out()
    let p = PlayerModel(output: out, fetcher: Fetcher(), defaults: defaults)
    p.configure(urls: try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
    return (p, out)
}

@MainActor
private func until(_ condition: () -> Bool) async {
    for _ in 0..<500 where !condition() { try? await Task.sleep(for: .milliseconds(10)) }
}

@MainActor
struct SavedPositionTests {
    private func savedAt120() async throws -> UserDefaults {
        let d = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let (p, out) = try player(d)
        p.play(songs(3))
        await until { p.phase == .playing }
        out.position = 120
        p.persist()
        return d
    }

    @Test func aNewAlbumStartsAtTheTopNotAtTheSavedPlace() async throws {
        let d = try await savedAt120()
        let (p, out) = try player(d)
        p.play(songs(2))
        await until { p.phase == .playing }
        #expect(out.seeks.isEmpty)
        #expect(p.position == 0)
    }

    @Test func nextAfterARestoreAlsoStartsAtTheTop() async throws {
        let d = try await savedAt120()
        let (p, out) = try player(d)
        p.next()
        await until { p.phase == .playing }
        #expect(out.seeks.isEmpty)
    }

    @Test func playOnTheRestoredQueueStillResumesWhereItWas() async throws {
        let d = try await savedAt120()
        let (p, out) = try player(d)
        p.togglePlayPause()
        await until { p.phase == .playing }
        #expect(out.seeks == [120])
    }
}

@MainActor
struct BackTargetTests {
    @Test func anAlbumOpenedFromAlbumsGoesBackToAlbums() {
        let s = AppState(screen: .albums)
        s.open(album: Fixtures.albums[0])
        #expect(s.screen == .album && s.albumBack == .albums)
    }

    @Test func anAlbumOpenedFromRecentlyAddedGoesBackThere() {
        let s = AppState(screen: .recent)
        s.open(album: Fixtures.albums[0])
        #expect(s.albumBack == .recent)
        s.open(album: Fixtures.albums[1])    // from an album page (similar album): the way back does not change
        #expect(s.albumBack == .recent)
    }

    @Test func anArtistOpenedFromTheArtistsListGoesBackToIt() {
        let s = AppState(screen: .artists)
        s.open(artist: ArtistItem(id: 1, name: "Can", albumCount: 3))
        #expect(s.screen == .artist && s.artistBack == .artists)
    }

    @Test func theArtistsRowShowsTheListNotTheLastArtist() {
        let s = AppState(screen: .artist)
        s.screen = .artists
        #expect(s.screen == .artists)
        #expect(AppState.title(of: .artists) == "Artists" && AppState.title(of: .recent) == "Recently Added")
    }
}

@MainActor
struct ToastTests {
    @Test func aFinishedGetShowsAToastThatThenGoesAway() async {
        let a = AcquisitionModel(defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        a.toastLifetime = .milliseconds(80)
        a.post(GetFinishedEvent(id: "x", outcome: .imported, title: "Added to your library", body: "One by A is ready to play."))
        a.post(GetFinishedEvent(id: "y", outcome: .failed, title: "Could not get Two", body: "A: no matches"))
        #expect(a.toasts.map(\.outcome) == [.imported, .failed])
        await until { a.toasts.isEmpty }
        #expect(a.toasts.isEmpty)
    }

    @Test func theToastLifetimeIsThirtySeconds() {
        let a = AcquisitionModel(defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        #expect(a.toastLifetime == .seconds(30))
    }

    @Test func onlyTheNewestFourStay() {
        let a = AcquisitionModel(defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        for i in 0..<6 { a.post(GetFinishedEvent(id: "\(i)", outcome: .imported, title: "t\(i)", body: "")) }
        #expect(a.toasts.map(\.title) == ["t2", "t3", "t4", "t5"])
    }
}

@MainActor
struct SongPagingTests {
    @Test func pagesHoldOneHundredSongs() {
        #expect(CupertinoLibrary.pageSize == 100)
        #expect([0, 1, 100].map(CupertinoLibrary.pageCount) == [1, 1, 1])
        #expect([101, 200, 201, 12_672].map(CupertinoLibrary.pageCount) == [2, 2, 3, 127])
    }
}

struct RelatedDecodingTests {
    private let albumJSON = #"""
    {"sections":{"similar_artists":{"items":[
      {"name":"George Harrison","key":"george harrison","artwork_url":null,"owned":false,"id":null},
      {"name":"Paul McCartney","key":"paul mccartney","artwork_url":"https://cdn.example/p.jpg","owned":true,"id":"ab12"},
      {"name":"","key":"x","owned":false},
      {"name":"Paul McCartney","key":"paul mccartney","owned":true}]},
     "similar_albums":{"items":[
      {"name":"All Things Must Pass","artist":"George Harrison","key":"george harrison/all things must pass","year":null,"owned":false},
      {"name":"Owned One","artist":"A","key":"a/owned one","owned":true}]},
     "tracks":{"items":[{"title":"Taxman","track_number":1,"duration_seconds":159}]}}}
    """#

    @Test func theAlbumPageGivesSimilarArtistsAlbumsAndTracks() throws {
        let page = try JSONDecoder().decode(AlbumPageEnvelope.self, from: Data(albumJSON.utf8)).related
        #expect(page.similarArtists.count == 4)
        #expect(page.similarAlbums.map(\.name) == ["All Things Must Pass"])      // only albums the library lacks
        #expect(page.tracks.map(\.title) == ["Taxman"])
        #expect(page.similarArtists[1].artworkURL?.absoluteString == "https://cdn.example/p.jpg" && page.similarArtists[1].owned)
    }

    @MainActor @Test func emptyAndRepeatedNamesAreDroppedAndOwnedAreSplitOut() throws {
        let page = try JSONDecoder().decode(AlbumPageEnvelope.self, from: Data(albumJSON.utf8)).related
        let cleaned = RelatedModel.cleaned(page.similarArtists)
        #expect(cleaned.map(\.name) == ["George Harrison", "Paul McCartney"])
    }

    @Test func pageKeysFollowTheServersForm() {
        #expect(LibrarianClient.key("The Beatles") == "beatles")
        #expect(LibrarianClient.key("Abd Al Malik") == "abd%20al%20malik")
        #expect(LibrarianClient.key("All Things Must Pass (2014 Remaster)") == "all%20things%20must%20pass%202014%20remaster")
        #expect(LibrarianClient.key("AC/DC") == "ac%20dc")
    }

    @Test func relativeArtworkAddressesAreNotUsed() throws {
        let a = try JSONDecoder().decode(SimilarArtistEntry.self, from: Data(#"{"name":"X","artwork_url":"/api/owned/artwork/1"}"#.utf8))
        #expect(a.artworkURL == nil)
    }
}

@MainActor
struct PaletteAndBackTests {
    @Test func theArtistsAndRecentlyAddedScreensAreInThePalette() {
        let titles = PaletteCatalog.results(query: "", playing: false, albums: [], artists: []).map(\.title)
        #expect(titles.contains("Go to Artists") && titles.contains("Go to Recently Added"))
    }

    @Test func anAlbumOpenedFromTheUpNextViewGoesBackToAlbums() {
        let s = AppState(screen: .queue)
        s.open(album: Fixtures.albums[0])
        #expect(s.albumBack == .albums && AppState.title(of: s.albumBack) == "Albums")
        let t = AppState(screen: .queue)
        t.open(artist: ArtistItem(id: 1, name: "Can", albumCount: 1))
        #expect(t.artistBack == .albums)
    }

    @Test func aTrackIsCurrentWhenTheSongPlayingIsItsOwn() {
        let s = AppState(screen: .album)
        let track = TrackItem(id: 0, title: "T0", duration: "", format: "", owned: true, playing: false)
        #expect(!s.isCurrent(track))
    }
}

@MainActor
struct QueueAndNowPlayingTests {
    @Test func theQueueButtonOpensUpNextWithoutLeavingTheScreen() {
        let s = AppState(themeID: .cupertino, screen: .library)
        s.go(.queue)
        #expect(s.queueOpen && s.screen == .library)
        s.go(.queue)
        #expect(!s.queueOpen && s.screen == .library)
    }

    @Test func zineKeepsUpNextAsItsOwnPage() {
        let s = AppState(themeID: .zine, screen: .home)
        s.go(.queue)
        #expect(s.screen == .queue && !s.queueOpen)
    }

    @Test func theNowPlayingNamesOpenTheAlbumAndTheArtist() async throws {
        let d = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let (p, _) = try player(d)
        p.play([QueueItem(songID: "s1", title: "T", artist: "Talk Talk", album: "Laughing Stock", albumID: "al1", duration: 200, suffix: "flac", track: 1, disc: 1)])
        let s = AppState(screen: .nowPlaying)
        s.player.play([QueueItem(songID: "s1", title: "T", artist: "Talk Talk", album: "Laughing Stock", albumID: "al1", duration: 200, suffix: "flac", track: 1, disc: 1)])
        s.openCurrentAlbum()
        #expect(s.screen == .album && s.selectedAlbum.title == "Laughing Stock" && s.selectedAlbum.remoteID == "al1")
    }
}

struct ArtistPageDecodingTests {
    private let json = #"""
    {"sections":{
      "bio":{"bio":{"text":"  Rapper and poet.  ","source":"Wikidata"}},
      "top_songs":{"items":[
        {"rank":2,"name":"Les Autres","listen_count":4963,"source":"listenbrainz","owned":true,"album":"Gibraltar"},
        {"rank":1,"name":"Gibraltar","listen_count":7611,"source":"listenbrainz","owned":false,"album":"Gibraltar"},
        {"rank":3,"name":"","listen_count":1}]},
      "similar":{"items":[{"name":"Oxmo Puccino","key":"oxmo puccino","owned":false}]}}}
    """#

    @Test func bioTopSongsAndSimilarComeFromTheArtistPage() throws {
        let page = try JSONDecoder().decode(ArtistPageEnvelope.self, from: Data(json.utf8)).related
        #expect(page.bio == "Rapper and poet." && page.bioSource == "Wikidata")
        #expect(page.topSongs.map(\.name) == ["Gibraltar", "Les Autres"])          // ranked, the nameless one dropped
        #expect(page.topSongs[0].listensText == "7.6K" && page.topSongs[1].owned)
        #expect(page.similar.map(\.name) == ["Oxmo Puccino"])
    }

    @Test func listenCountsAreShortened() {
        #expect(TopSongEntry(rank: 1, name: "a", listenCount: 950).listensText == "950")
        #expect(TopSongEntry(rank: 1, name: "a", listenCount: 1_250_000).listensText == "1.2M")
        #expect(TopSongEntry(rank: 1, name: "a").listensText == nil)
    }
}

@MainActor
struct UnownedArtistAndRetryTests {
    @Test func aSimilarArtistTheLibraryLacksOpensItsOwnPage() {
        let s = AppState(screen: .album)
        s.open(similar: SimilarArtistEntry(name: "Oxmo Puccino", owned: false))
        #expect(s.screen == .artist && s.selectedArtist.name == "Oxmo Puccino")
        #expect(s.artistBack == .album)
    }

    @Test func theArtistPageAlbumsComeFromTheLibrarianOnlyForAnArtistTheLibraryLacks() {
        let s = AppState(screen: .artists)
        #expect(!s.selectedArtistIsUnowned)      // sample data: nothing is "live", so the library's own list is used
        #expect(s.shownArtistAlbums == s.library.artistAlbums)
    }

    @Test func aPartialPageIsDecodedAsPartial() throws {
        let json = #"{"sections":{"bio":{"bio":null},"albums":{"items":[{"name":"Gibraltar","year":2006,"owned":false,"key":"abd al malik/gibraltar"}]}},"done":{"partial":true}}"#
        let page = try JSONDecoder().decode(ArtistPageEnvelope.self, from: Data(json.utf8)).related
        #expect(page.partial && page.bio == nil)
        #expect(page.albums.map(\.name) == ["Gibraltar"] && page.albums[0].year == 2006)
    }

    @Test func aFailedAskIsNotRememberedSoTheNextVisitAsksAgain() async {
        let r = RelatedModel()
        r.retryPause = .milliseconds(1)
        await r.loadArtist(name: "Nobody", remoteID: nil, librarian: nil)      // no Librarian: nothing is kept
        #expect(r.artists.isEmpty && !r.loading)
        await r.loadArtist(name: "Nobody", remoteID: nil, librarian: nil)
        #expect(r.bio == nil)
    }
}
