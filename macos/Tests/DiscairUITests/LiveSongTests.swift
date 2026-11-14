import AppKit
import DiscairAudio
import DiscairCore
import DiscairLibrarian
import Foundation
import MediaPlayer
import Testing
@testable import DiscairAudio
@testable import DiscairUI

/// Answers `/now` from a script and records which stations were asked about.
final class FakeNowSource: LiveNowSource, @unchecked Sendable {
    private let lock = NSLock()
    private var _answer: RadioNow = RadioNow(state: .idle)
    private var _asked: [String] = []
    private var _fail = false
    var answer: RadioNow { get { lock.withLock { _answer } } set { lock.withLock { _answer = newValue } } }
    var asked: [String] { lock.withLock { _asked } }
    var fail: Bool { get { lock.withLock { _fail } } set { lock.withLock { _fail = newValue } } }
    func radioNow(station: String) async throws -> RadioNow {
        lock.withLock { _asked.append(station) }
        if fail { throw DiscairError.server(status: 500, message: nil) }
        return answer
    }
}

final class FakeGetSource: RadioGetSource, @unchecked Sendable {
    private let lock = NSLock()
    private var _result = RadioGetResult.make(ok: true, message: "Requested “Moon Safari”.")
    private var _sent: [Int] = []
    private var _error: DiscairError?
    var result: RadioGetResult { get { lock.withLock { _result } } set { lock.withLock { _result = newValue } } }
    var error: DiscairError? { get { lock.withLock { _error } } set { lock.withLock { _error = newValue } } }
    var sent: [Int] { lock.withLock { _sent } }
    func getRadioPlay(id: Int) async throws -> RadioGetResult {
        lock.withLock { _sent.append(id) }
        if let error { throw error }
        return result
    }
}

extension RadioGetResult {
    static func make(ok: Bool, message: String? = nil) -> RadioGetResult {
        var json: [String: Any] = ["ok": ok]
        if let message { json["message"] = message }
        return try! JSONDecoder().decode(RadioGetResult.self, from: JSONSerialization.data(withJSONObject: json))
    }
}

@MainActor
private final class QuietEngine: AudioOutput {
    var onFinished: (() -> Void)?
    var onAdvanced: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 0
    var volume: Float = 1
    func open(file: URL) throws {}
    func play() {}
    func pause() {}
    func stop() {}
    func seek(to seconds: Double) {}
    func preload(file: URL, transition: Transition) throws {}
    func cancelPreload() {}
    func applyEQ(gains: [Double], preGain: Double) {}
    func restoreOutputRate() {}
}

private func song(_ artist: String, _ title: String, playID: Int? = nil, inLibrary: Bool = false, cover: String? = nil) -> RadioNow {
    RadioNow(state: .ok, rawTitle: "\(artist) - \(title)", artist: artist, title: title, playID: playID, inLibrary: inLibrary, coverPath: cover)
}

@MainActor
private func make(proxied: Bool = true) -> (PlayerModel, FakeNowSource, RadioStation) {
    let defaults = UserDefaults(suiteName: "discair-livesong-\(UUID().uuidString)")!
    let p = PlayerModel(output: QuietEngine(), defaults: defaults, liveOutput: FakeLiveOutput())
    p.liveBase = URL(string: "http://librarian.example.invalid:8689")
    // The timer never fires in tests; a test calls `pollLiveNow()` itself.
    p.liveNowPause = { _ in try? await Task.sleep(for: .seconds(3600)) }
    let source = FakeNowSource()
    p.liveNowSource = source
    let station = RadioStation(id: "7", name: "FIP", proxied: proxied, playableURL: "/radio/stream/tok7")
    return (p, source, station)
}

@MainActor
@Suite("Live song") struct LiveSongTests {
    // MARK: Words of every state (contract section 6)

    @Test func everyStateHasWordsAndOnlyOkIsASong() {
        #expect(LiveSongLine.of(song("Air", "La Femme d'Argent")).songText == "Air – La Femme d'Argent")
        #expect(LiveSongLine.of(song("Air", "La Femme d'Argent")).hasSong)
        #expect(LiveSongLine.of(RadioNow(state: .noMetadata)).sentence == "This station sends no song titles.")
        #expect(LiveSongLine.of(RadioNow(state: .unknown)).sentence == "This station sends no song titles.")
        #expect(LiveSongLine.of(RadioNow(state: .notProxied)).sentence == "Not relayed · no song titles.")
        #expect(LiveSongLine.of(RadioNow(state: .unavailable)).sentence == "Station unreachable.")
        #expect(LiveSongLine.of(RadioNow(state: .idle)).sentence == "On air")
        #expect(LiveSongLine.of(nil).sentence == "On air")
    }

    @Test func anUnmatchedTitleIsShownRawWithTheReason() {
        let line = LiveSongLine.of(RadioNow(state: .unparsed, rawTitle: "Jingle 7"))
        #expect(!line.hasSong && line.title == "Jingle 7")
        #expect(line.sentence == "The title could not be matched to an artist and song.")
    }

    @Test func theConnectionStateComesBeforeTheTitle() {
        let now = song("Air", "Playground Love")
        #expect(LiveSongLine.of(now, phase: .playing).hasSong)
        #expect(LiveSongLine.of(now, phase: .connecting).sentence == "Connecting…")
        #expect(LiveSongLine.of(now, phase: .reconnecting).sentence == "Reconnecting…")
        #expect(LiveSongLine.of(now, phase: .unreachable).sentence == "Station unreachable")
        #expect(!LiveSongLine.of(now, phase: .reconnecting).hasSong)
    }

    @Test func theBarLinesAreTheSongOrTheStation() {
        let withSong = LiveSongLine.of(song("Air", "Playground Love"))
        #expect(withSong.headline(station: "FIP") == "Playground Love" && withSong.detail == "Air")
        let without = LiveSongLine.of(RadioNow(state: .noMetadata))
        #expect(without.headline(station: "FIP") == "FIP" && without.detail == "This station sends no song titles.")
    }

    // MARK: The 5 s poll

    @Test func aPollFillsTheLiveSongAndMarksWhenItWasFirstSeen() async {
        let (p, source, station) = make()
        p.playStation(station)
        p.liveStateChanged(.playing)
        source.answer = song("Air", "Playground Love", playID: nil)
        await p.pollLiveNow()
        #expect(p.liveNow?.title == "Playground Love" && p.liveSongSince != nil)
        #expect(p.liveLine.songText == "Air – Playground Love")
        #expect(source.asked.allSatisfy { $0 == "7" })
    }

    @Test func aNewTitleRestartsTheListeningClockAndTheSameTitleDoesNot() async {
        let (p, source, station) = make()
        p.playStation(station)
        source.answer = song("Air", "One"); await p.pollLiveNow()
        let first = p.liveSongSince
        source.answer = song("Air", "One", playID: 4); await p.pollLiveNow()      // heard for 30 s: same song
        #expect(p.liveSongSince == first && p.liveNow?.playID == 4)
        try? await Task.sleep(for: .milliseconds(20))
        source.answer = song("Air", "Two"); await p.pollLiveNow()
        #expect(p.liveSongSince != first)
    }

    @Test func aFailedReadKeepsTheLastSong() async {
        let (p, source, station) = make()
        p.playStation(station)
        source.answer = song("Air", "One"); await p.pollLiveNow()
        source.fail = true; await p.pollLiveNow()
        #expect(p.liveNow?.title == "One")
    }

    @Test func aStationThatIsNotRelayedIsNotAskedAboutAndSaysSo() async {
        let (p, source, station) = make(proxied: false)
        p.playStation(station)
        p.liveStateChanged(.playing)
        await p.pollLiveNow()
        #expect(p.liveNow?.state == .notProxied && p.liveLine.sentence == "Not relayed · no song titles.")
        #expect(source.asked.isEmpty)
    }

    @Test func stoppingClearsTheSongAndALateAnswerIsDropped() async {
        let (p, source, station) = make()
        p.playStation(station)
        source.answer = song("Air", "One"); await p.pollLiveNow()
        p.stopStation()
        #expect(p.liveNow == nil && p.liveSongSince == nil)
        await p.pollLiveNow()                      // nothing plays: nothing is asked
        #expect(p.liveNow == nil)
    }

    @Test func anotherStationStartsWithoutTheOldSong() async {
        let (p, source, station) = make()
        p.playStation(station)
        source.answer = song("Air", "One"); await p.pollLiveNow()
        p.playStation(RadioStation(id: "8", name: "KEXP", proxied: true, playableURL: "/radio/stream/tok8"))
        #expect(p.liveNow == nil)
    }

    @Test func aTitleChangeTellsTheSystemOnce() async {
        let (p, source, station) = make()
        var told = 0
        p.onNowPlayingChange = { told += 1 }
        p.playStation(station)
        let base = told
        source.answer = song("Air", "One"); await p.pollLiveNow(); await p.pollLiveNow()
        #expect(told == base + 1)
    }

    // MARK: Download

    @Test func theLiveSongsDownloadFollowsTheContractRules() {
        let d = RadioDownloads()
        #expect(d.state(now: nil) == .none)
        #expect(d.state(now: song("Air", "One")) == .waiting)
        #expect(d.state(now: song("Air", "One", playID: 4)) == .ready)
        #expect(d.state(now: song("Air", "One", playID: 4, inLibrary: true)) == .owned)
        #expect(d.state(now: RadioNow(state: .noMetadata)) == .none)
        #expect(d.state(now: RadioNow(state: .unparsed, rawTitle: "x", playID: 3)) == .none)
    }

    @Test func aGetSendsOnceKeepsTheServersSentenceAndReloadsHeard() async {
        let d = RadioDownloads(), source = FakeGetSource()
        var reloads = 0
        d.configure(source: source); d.onSuccess = { reloads += 1 }
        await d.get(playID: 4)
        #expect(source.sent == [4] && reloads == 1)
        #expect(d.sentence(for: 4) == "Requested “Moon Safari”.")
        #expect(d.state(now: song("Air", "One", playID: 4)) == .done)
        await d.get(playID: 4)                                  // already asked for
        #expect(source.sent == [4])
    }

    @Test func aRefusalOffersTryAgainWithTheSentenceAndSendsAgainOnTheNextClick() async {
        let d = RadioDownloads(), source = FakeGetSource()
        var reloads = 0
        d.configure(source: source); d.onSuccess = { reloads += 1 }
        source.result = RadioGetResult.make(ok: false, message: "No match on any indexer.")
        await d.get(playID: 4)
        #expect(d.state(now: song("Air", "One", playID: 4)) == .failed)
        #expect(d.sentence(for: 4) == "No match on any indexer." && reloads == 0)
        source.result = RadioGetResult.make(ok: true)
        await d.get(playID: 4)
        #expect(source.sent == [4, 4] && d.state(now: song("Air", "One", playID: 4)) == .done && reloads == 1)
    }

    @Test func aNetworkFailureIsATryAgainWithWords() async {
        let d = RadioDownloads(), source = FakeGetSource()
        d.configure(source: source)
        source.error = DiscairError.server(status: 503, message: "The Librarian is busy.")
        await d.get(playID: 9)
        #expect(d.state(now: song("A", "B", playID: 9)) == .failed)
        #expect(d.sentence(for: 9) == "The Librarian is busy.")
    }

    @Test func anotherSongStartsFromItsOwnState() async {
        let d = RadioDownloads(), source = FakeGetSource()
        d.configure(source: source)
        await d.get(playID: 4)
        #expect(d.state(now: song("A", "Next", playID: 5)) == .ready)
    }

    // MARK: Where the song is shown

    @Test func theMiniPlayerShowsTheSongOverArtistAndStation() {
        let live = LiveSession(stationID: "7", name: "FIP", logoPath: "", startedAt: Date(), phase: .playing)
        let c = MiniPlayerContent(current: nil, upNext: [], live: live, liveNow: song("Air", "Playground Love"))
        #expect(c.title == "Playground Love" && c.artist == "Air · FIP" && c.isLive)
        let none = MiniPlayerContent(current: nil, upNext: [], live: live, liveNow: RadioNow(state: .noMetadata))
        #expect(none.title == "FIP" && none.artist == "This station sends no song titles.")
    }

    @Test func theSystemGetsTitleArtistAndTheStationAsAlbum() {
        let line = LiveSongLine.of(song("Air", "Playground Love"))
        let info = SystemMedia.liveInfo(stationName: "FIP", song: line, cover: nil)
        #expect(info[MPMediaItemPropertyTitle] as? String == "Playground Love")
        #expect(info[MPMediaItemPropertyArtist] as? String == "Air")
        #expect(info[MPMediaItemPropertyAlbumTitle] as? String == "FIP")
        #expect(info[MPNowPlayingInfoPropertyIsLiveStream] as? Bool == true)
        #expect(info[MPMediaItemPropertyPlaybackDuration] == nil)
        let plain = SystemMedia.liveInfo(stationName: "FIP", song: LiveSongLine.of(RadioNow(state: .noMetadata)), cover: nil)
        #expect(plain[MPMediaItemPropertyTitle] as? String == "FIP" && plain[MPMediaItemPropertyArtist] == nil)
    }
}
