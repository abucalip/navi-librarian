import DiscairAudio
import DiscairNavidrome
import Foundation
import Observation

/// Playback state for the screens: what is playing, the queue, position, and the controls. Themes read this and call
/// it; the audio engine and the downloads stay behind it.
@MainActor
@Observable
public final class PlayerModel {
    public enum Phase: Equatable, Sendable { case idle, loading, playing, paused, failed(String) }

    public private(set) var queue = PlayQueue()
    public private(set) var phase: Phase = .idle
    public private(set) var position: Double = 0
    public private(set) var duration: Double = 0
    /// Songs finished or left this session, newest first (the queue's History).
    public private(set) var history: [QueueItem] = []
    /// Crossfade length in seconds; 0 is off. Continuous albums stay gapless whatever this is.
    public var crossfadeSeconds: Int {
        didSet {
            guard crossfadeSeconds != oldValue else { return }
            defaults.set(crossfadeSeconds, forKey: Self.crossfadeKey)
            refreshPreload()
        }
    }
    public static let crossfadeChoices = [0, 2, 4, 6, 8, 10]
    private static let crossfadeKey = "discair.crossfadeSeconds"
    /// App output level 0...1 (remembered).
    public var volume: Float {
        didSet { output.volume = volume; defaults.set(Double(volume), forKey: Self.volumeKey) }
    }
    /// The equalizer (remembered). Change it through `updateEQ`.
    public private(set) var eq = EQSettings()
    private static let volumeKey = "discair.volume"
    private static let eqKey = "discair.equalizer"
    private static let queueKey = "discair.queue"
    public static let positionKey = "discair.queuePosition"
    public var current: QueueItem? { queue.current }
    public var isPlaying: Bool { phase == .playing }
    public var shuffle: Bool { queue.shuffle }
    public var repeatMode: RepeatMode { queue.repeatMode }
    /// 0...1 for the progress bars.
    public var fraction: Double { duration > 0 ? min(max(position / duration, 0), 1) : 0 }

    @ObservationIgnored private var urls: StreamURLBuilder?
    @ObservationIgnored private let output: AudioOutput
    @ObservationIgnored private let fetcher: AudioFetcher
    @ObservationIgnored private var loadTask: Task<Void, Never>?
    @ObservationIgnored private var tickTask: Task<Void, Never>?
    @ObservationIgnored private var loadGeneration = 0
    @ObservationIgnored private var downloaded: URL?
    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private var preloadTask: Task<Void, Never>?
    /// The song handed to the engine (or being fetched) as the follower, and its file once downloaded.
    @ObservationIgnored private var preloaded: (id: UUID, file: URL?)?

    public init(output: AudioOutput = EngineOutput(), fetcher: AudioFetcher = URLSessionFetcher(), defaults: UserDefaults = .standard) {
        self.output = output
        self.fetcher = fetcher
        self.defaults = defaults
        let saved = defaults.integer(forKey: Self.crossfadeKey)
        crossfadeSeconds = Self.crossfadeChoices.contains(saved) ? saved : 0
        let v = defaults.object(forKey: Self.volumeKey) as? Double
        volume = Float(min(max(v ?? 1, 0), 1))
        output.volume = volume
        if let data = defaults.data(forKey: Self.eqKey), let saved = try? JSONDecoder().decode(EQSettings.self, from: data) { eq = saved }
        output.applyEQ(gains: eq.effective.gains, preGain: eq.effective.preGain)
        if let data = defaults.data(forKey: Self.queueKey), let snap = try? JSONDecoder().decode(PlayQueue.Snapshot.self, from: data), !snap.items.isEmpty {
            queue = PlayQueue(snapshot: snap)
            resumeAt = defaults.double(forKey: Self.positionKey)
            position = resumeAt
            duration = queue.current?.duration ?? 0
        }
        output.onFinished = { [weak self] in self?.songEnded() }
        output.onAdvanced = { [weak self] in self?.advancedByEngine() }
    }

    /// Seconds to jump to when the restored song first starts (0 otherwise).
    @ObservationIgnored private var resumeAt: Double = 0

    // MARK: Equalizer

    public func updateEQ(_ change: (inout EQSettings) -> Void) {
        change(&eq)
        defaults.set(try? JSONEncoder().encode(eq), forKey: Self.eqKey)
        output.applyEQ(gains: eq.effective.gains, preGain: eq.effective.preGain)
    }

    // MARK: Saving the queue

    /// Writes the queue and the position. Called when the queue changes, a song changes, playback pauses and every few
    /// seconds while playing; the cost is one small JSON write.
    public func persist() {
        let snap = queue.snapshot
        guard !snap.items.isEmpty else { defaults.removeObject(forKey: Self.queueKey); defaults.removeObject(forKey: Self.positionKey); return }
        let capped = snap.items.count > 500 && snap.index.map({ $0 < 500 }) == true
            ? PlayQueue.Snapshot(items: Array(snap.items.prefix(500)), index: snap.index, shuffle: snap.shuffle, repeatMode: snap.repeatMode) : snap
        defaults.set(try? JSONEncoder().encode(capped), forKey: Self.queueKey)
        defaults.set(phase == .idle ? resumeAt : (output.position > 0 ? output.position : position), forKey: Self.positionKey)
    }

    public func configure(urls: StreamURLBuilder?) {
        self.urls = urls
        if urls == nil { stop() }
    }

    // MARK: Starting

    /// Plays `songs` from `startAt`, replacing the queue.
    public func play(_ songs: [QueueItem], startAt: Int = 0) {
        queue.set(songs, startAt: startAt)
        startCurrent()
    }

    public func playNext(_ song: QueueItem) {
        let wasEmpty = queue.isEmpty
        queue.playNext(song)
        if wasEmpty { startCurrent() } else { refreshPreload(); persist() }
    }

    public func addToQueue(_ song: QueueItem) {
        let wasEmpty = queue.isEmpty
        queue.append(song)
        if wasEmpty { startCurrent() } else { refreshPreload(); persist() }
    }

    // MARK: Controls

    public func togglePlayPause() {
        switch phase {
        case .playing: output.pause(); phase = .paused; position = output.position; stopTicking(); persist()
        case .paused: output.play(); phase = .playing; startTicking()
        case .idle, .failed: if current != nil { startCurrent() }
        case .loading: break
        }
    }

    public func next() {
        pushHistory()
        guard queue.advance(natural: false) != nil else { stop(); return }
        startCurrent()
    }

    /// Past three seconds, Previous restarts the song; otherwise it goes back one.
    public func previous() {
        if phase == .playing || phase == .paused, output.position > 3 { seek(toSeconds: 0); return }
        guard queue.back() != nil else { return }
        if !history.isEmpty { history.removeFirst() }
        startCurrent()
    }

    public func seek(toFraction f: Double) { seek(toSeconds: duration * min(max(f, 0), 1)) }

    public func seek(toSeconds s: Double) {
        guard phase == .playing || phase == .paused else { return }
        output.seek(to: s)
        position = output.position
    }

    public func toggleShuffle() { queue.setShuffle(!queue.shuffle); refreshPreload(); persist() }

    public func cycleRepeat() {
        queue.repeatMode = switch queue.repeatMode { case .off: .all; case .all: .one; case .one: .off }
        refreshPreload(); persist()
    }

    public func removeUpNext(at i: Int) { queue.removeUpNext(at: i); refreshPreload(); persist() }
    public func moveUpNext(from: Int, to: Int) { queue.moveUpNext(from: from, to: to); refreshPreload(); persist() }

    /// Plays a song from Up Next now; the songs skipped over stay in the queue behind it.
    public func jump(toUpNext i: Int) {
        pushHistory()
        queue.jump(upNext: i)
        startCurrent()
    }

    /// Empties Up Next; the current song keeps playing.
    public func clearUpNext() { queue.clearUpNext(); refreshPreload(); persist() }

    public func stop() {
        loadGeneration += 1
        loadTask?.cancel()
        dropPreload()
        output.stop()
        stopTicking()
        phase = .idle; position = 0; duration = 0; resumeAt = 0
        cleanUp()
    }

    // MARK: Loading

    /// What to ask Navidrome for. Vorbis and WMA files go through the server as opus at 192 (owner decision, contract 12.8).
    static func streamOptions(suffix: String?) -> (format: TranscodeFormat?, bitRate: Int?) {
        switch (suffix ?? "").lowercased() {
        case "ogg", "oga", "wma": (.opus, 192)
        default: (nil, nil)
        }
    }

    private func startCurrent() {
        guard let item = queue.current else { stop(); return }
        guard let urls else { phase = .failed("Not connected to Navidrome. Check Settings."); return }
        loadGeneration += 1
        let mine = loadGeneration
        loadTask?.cancel()
        dropPreload()
        output.stop(); stopTicking()
        let startAt = resumeAt; resumeAt = 0
        phase = .loading; position = startAt; duration = item.duration
        persist()
        let opts = Self.streamOptions(suffix: item.suffix)
        loadTask = Task { [weak self, fetcher] in
            do {
                let url = try urls.streamURL(songID: item.songID, maxBitRate: opts.bitRate, format: opts.format)
                let file = try await fetcher.fetch(url, suffix: opts.format?.rawValue ?? item.suffix)
                guard let self, !Task.isCancelled, self.loadGeneration == mine else { try? FileManager.default.removeItem(at: file); return }
                self.cleanUp()
                self.downloaded = file
                try self.output.open(file: file)
                self.duration = self.output.duration
                if startAt > 3, startAt < self.duration - 3 { self.output.seek(to: startAt); self.position = startAt }
                self.output.play()
                self.phase = .playing
                self.startTicking()
                self.refreshPreload()
            } catch {
                guard let self, self.loadGeneration == mine else { return }
                self.phase = .failed((error as? AudioError)?.description ?? "The song could not be played.")
            }
        }
    }

    private func songEnded() {
        stopTicking()
        pushHistory()
        if queue.advance(natural: true) != nil { startCurrent() }
        else { dropPreload(); phase = .idle; position = 0; cleanUp() }
    }

    private func pushHistory() {
        if let c = queue.current { history.insert(c, at: 0); if history.count > 50 { history.removeLast() } }
    }

    // MARK: Preload (gapless and crossfade)

    /// Two songs of one album, in track order, belong together: no fade between them whatever the setting.
    static func isContinuous(_ a: QueueItem, _ b: QueueItem) -> Bool {
        guard let ai = a.albumID, ai == b.albumID, let at = a.track, let bt = b.track else { return false }
        let ad = a.disc ?? 1, bd = b.disc ?? 1
        return (bd == ad && bt == at + 1) || (bd == ad + 1 && bt == 1)
    }

    static func transition(from a: QueueItem, to b: QueueItem, crossfade: Int) -> Transition {
        crossfade > 0 && !isContinuous(a, b) ? .crossfade(Double(crossfade)) : .gapless
    }

    /// Makes sure the engine holds the song that will really follow. Called after anything that changes what is next.
    private func refreshPreload() {
        guard phase == .playing || phase == .paused, let now = queue.current, let next = queue.peekNext, let urls else {
            if phase == .playing || phase == .paused { dropPreload() }
            return
        }
        if preloaded?.id == next.id { return }
        dropPreload()
        let transition = Self.transition(from: now, to: next, crossfade: crossfadeSeconds)
        let opts = Self.streamOptions(suffix: next.suffix)
        let mine = loadGeneration
        preloaded = (next.id, nil)
        preloadTask = Task { [weak self, fetcher] in
            guard let url = try? urls.streamURL(songID: next.songID, maxBitRate: opts.bitRate, format: opts.format),
                  let file = try? await fetcher.fetch(url, suffix: opts.format?.rawValue ?? next.suffix) else { return }
            guard let self, !Task.isCancelled, self.loadGeneration == mine, self.preloaded?.id == next.id, self.queue.peekNext?.id == next.id else {
                try? FileManager.default.removeItem(at: file); return
            }
            do { try self.output.preload(file: file, transition: transition); self.preloaded = (next.id, file) }
            catch { try? FileManager.default.removeItem(at: file); self.preloaded = nil }
        }
    }

    /// Forgets the follower: stops its download, takes it out of the engine and deletes its file.
    private func dropPreload() {
        preloadTask?.cancel(); preloadTask = nil
        if let p = preloaded {
            output.cancelPreload()
            if let f = p.file { try? FileManager.default.removeItem(at: f) }
        }
        preloaded = nil
    }

    /// The engine started the preloaded song by itself (a gapless join or the start of a fade).
    private func advancedByEngine() {
        guard let p = preloaded, queue.peekNext?.id == p.id else { return }
        pushHistory()
        queue.advance(natural: true)
        cleanUp()
        downloaded = p.file
        preloaded = nil
        position = output.position
        duration = output.duration
        phase = output.isPlaying ? .playing : .paused
        refreshPreload()
        persist()
    }

    private func cleanUp() {
        if let d = downloaded { try? FileManager.default.removeItem(at: d); downloaded = nil }
    }

    private func startTicking() {
        stopTicking()
        tickTask = Task { [weak self] in
            var n = 0
            while !Task.isCancelled {
                self?.position = self?.output.position ?? 0
                n += 1
                if n % 20 == 0 { self?.persist() }
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    private func stopTicking() { tickTask?.cancel(); tickTask = nil }
}

extension PlayerModel {
    static func item(_ s: NavidromeSong) -> QueueItem {
        QueueItem(songID: s.id, title: s.title, artist: s.artist ?? "Unknown artist", album: s.album ?? "", albumID: s.albumId,
                  coverArt: s.coverArt, duration: Double(s.duration ?? 0), suffix: s.suffix, track: s.track, disc: s.discNumber)
    }

    /// Sample rows (no server id) cannot be played.
    static func item(_ r: SongRow) -> QueueItem? {
        guard let id = r.remoteID else { return nil }
        return QueueItem(songID: id, title: r.title, artist: r.artist, album: r.cover?.title ?? "", albumID: r.cover?.remoteID,
                         coverArt: r.cover?.coverArt, duration: r.seconds, suffix: r.suffix, track: r.track, disc: r.disc)
    }

    /// "3:12" style clock for a number of seconds.
    public static func clock(_ seconds: Double) -> String {
        let s = Int(max(0, seconds)); return "\(s / 60):" + String(format: "%02d", s % 60)
    }
}
