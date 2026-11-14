import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairAudio
@testable import DiscairUI

/// Plays nothing; records what the model asked for (S2-2 item 2, the fake the proposal names).
@MainActor
final class FakeLiveOutput: LiveOutput {
    var onState: ((LiveState) -> Void)?
    var volume: Float = 1
    var started: [URL] = []
    var stops = 0
    func start(url: URL) { started.append(url) }
    func stop() { stops += 1 }
    func report(_ state: LiveState) { onState?(state) }
}

@MainActor
private final class QuietOutput: AudioOutput {
    var onFinished: (() -> Void)?
    var onAdvanced: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    var volume: Float = 1
    var seeks: [Double] = []
    var restores = 0
    func open(file: URL) throws {}
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) { seeks.append(seconds) }
    func preload(file: URL, transition: Transition) throws {}
    func cancelPreload() {}
    func applyEQ(gains: [Double], preGain: Double) {}
    func restoreOutputRate() { restores += 1 }
}

private final class QuietFetcher: AudioFetcher, @unchecked Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let f = FileManager.default.temporaryDirectory.appending(path: "live-\(UUID().uuidString).\(suffix ?? "bin")")
        try Data([0]).write(to: f)
        return f
    }
}

private func station(_ id: String, favourite: Bool = true, proxied: Bool = true, url: String? = nil) -> RadioStation {
    RadioStation(id: id, name: "Station \(id)", proxied: proxied, playableURL: url ?? "/radio/stream/tok\(id)", favourite: favourite)
}

private func songs(_ n: Int) -> [QueueItem] {
    (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A", album: "Al", duration: 200, suffix: "mp3", track: $0 + 1, disc: 1) }
}

@MainActor
private func make(favourites: [RadioStation] = []) throws -> (PlayerModel, FakeLiveOutput, QuietOutput, UserDefaults) {
    let live = FakeLiveOutput(), out = QuietOutput()
    let defaults = UserDefaults(suiteName: "discair-live-\(UUID().uuidString)")!
    let p = PlayerModel(output: out, fetcher: QuietFetcher(), defaults: defaults, liveOutput: live)
    p.configure(urls: try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
    p.liveBase = URL(string: "http://librarian.example.invalid:8689")
    p.favouriteStations = { favourites }
    return (p, live, out, defaults)
}

@MainActor
struct LiveSessionTests {
    @Test func startingAStationOpensItsResolvedAddressAndShowsConnecting() throws {
        let (p, live, _, defaults) = try make()
        p.playStation(station("7"))
        #expect(live.started == [URL(string: "http://librarian.example.invalid:8689/radio/stream/tok7")!])
        #expect(p.live?.stationID == "7" && p.live?.name == "Station 7" && p.live?.phase == .connecting)
        #expect(defaults.string(forKey: PlayerModel.lastStationKey) == "7")
    }

    @Test func theOutputsStatesBecomeThePhases() throws {
        let (p, live, _, _) = try make()
        p.playStation(station("1"))
        live.report(.playing); #expect(p.live?.phase == .playing)
        live.report(.stalled); #expect(p.live?.phase == .reconnecting)
        live.report(.failed); #expect(p.live?.phase == .unreachable)
    }

    @Test func aLibrarySongIsPausedAndTheQueueIsLeftAlone() async throws {
        let (p, _, out, _) = try make()
        p.play(songs(3))
        for _ in 0..<200 where p.phase != .playing { try? await Task.sleep(for: .milliseconds(10)) }
        #expect(p.phase == .playing)
        let before = p.queue.items.map(\.songID), index = p.queue.snapshot.index
        p.playStation(station("1"))
        #expect(p.phase == .paused && !out.isPlaying && out.restores >= 1)
        #expect(p.queue.items.map(\.songID) == before && p.queue.snapshot.index == index)
    }

    @Test func stoppingLeavesTheQueuePausedAndPlayStartsTheStationAgain() async throws {
        let (p, live, _, _) = try make()
        p.play(songs(2))
        for _ in 0..<200 where p.phase != .playing { try? await Task.sleep(for: .milliseconds(10)) }
        p.playStation(station("1"))
        p.togglePlayPause()                                   // stops the station
        #expect(p.live == nil && live.stops >= 1 && p.phase == .paused && p.queue.items.count == 2)
        p.togglePlayPause()                                   // starts it again, not the song
        #expect(p.live?.stationID == "1" && live.started.count == 2 && p.phase == .paused)
    }

    @Test func aLibrarySongStopsTheStationAndForgetsItForPlay() async throws {
        let (p, live, _, _) = try make()
        p.playStation(station("1"))
        p.play(songs(1))
        #expect(p.live == nil && live.stops >= 1)
        for _ in 0..<200 where p.phase != .playing { try? await Task.sleep(for: .milliseconds(10)) }
        p.togglePlayPause()                                   // pauses the song
        p.togglePlayPause()                                   // resumes the song, not a station
        #expect(p.live == nil && p.phase == .playing)
    }

    @Test func nextAndPreviousStepThroughFavouritesAndWrap() throws {
        let favs = [station("a"), station("b"), station("c")]
        let (p, _, _, _) = try make(favourites: favs)
        p.playStation(favs[0])
        p.next(); #expect(p.live?.stationID == "b")
        p.next(); p.next(); #expect(p.live?.stationID == "a")
        p.previous(); #expect(p.live?.stationID == "c")
    }

    @Test func aStationThatIsNotAFavouriteGoesToTheFirstOrLast() throws {
        let favs = [station("a"), station("b")]
        let (p, _, _, _) = try make(favourites: favs)
        p.playStation(station("x", favourite: false))
        p.next(); #expect(p.live?.stationID == "a")
        p.playStation(station("x", favourite: false))
        p.previous(); #expect(p.live?.stationID == "b")
    }

    @Test func withFewerThanTwoFavouritesNextAndPreviousDoNothing() throws {
        let (p, live, _, _) = try make(favourites: [station("a")])
        p.playStation(station("a"))
        p.next(); p.previous()
        #expect(p.live?.stationID == "a" && live.started.count == 1)
    }

    @Test func seekIsIgnoredWhileLive() async throws {
        let (p, _, out, _) = try make()
        p.play(songs(1))
        for _ in 0..<200 where p.phase != .playing { try? await Task.sleep(for: .milliseconds(10)) }
        p.playStation(station("1"))
        p.seek(toSeconds: 30); p.seek(toFraction: 0.5)
        #expect(out.seeks.isEmpty)
    }

    @Test func nothingAboutAStationIsSavedWithTheQueue() throws {
        let (p, _, _, defaults) = try make()
        p.playStation(station("9"))
        p.persist()
        #expect(defaults.data(forKey: "discair.queue") == nil)
        #expect(defaults.string(forKey: PlayerModel.lastStationKey) == "9")
    }

    @Test func aPlaylistAddressThatIsNotRelayedIsRefusedInWords() throws {
        let (p, live, _, _) = try make()
        p.playStation(station("1", proxied: false, url: "http://radio.example.invalid/live.pls"))
        #expect(p.live == nil && live.started.isEmpty)
        #expect(p.notice == "This station's address is a playlist the Mac cannot play. Switch its relay on from the web Radio page.")
        #expect(p.notice?.contains("example.invalid") == false)
    }

    @Test func aRelayedStationWithAPlaylistLikeNameStillPlays() throws {
        let (p, live, _, _) = try make()
        p.playStation(station("1", proxied: true, url: "http://relay.example.invalid/x.m3u"))
        #expect(live.started.count == 1)
    }

    @Test func theVolumeReachesTheLiveOutput() throws {
        let (p, live, _, _) = try make()
        p.volume = 0.4
        #expect(live.volume == 0.4)
    }
}
