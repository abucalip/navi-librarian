import DiscairAudio
import DiscairLibrarian
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
    public internal(set) var phase: Phase = .idle { didSet { onNowPlayingChange?() } }
    /// Told when the song or play state changes (the system Now Playing hook).
    @ObservationIgnored public var onNowPlayingChange: (() -> Void)?
    public internal(set) var position: Double = 0 { didSet { positionAnchor = Date() } }
    @ObservationIgnored private var positionAnchor = Date()
    /// The position for a clock on screen: the last reading carried forward by the time since it was taken (at most 2 s), so
    /// the clock keeps moving smoothly when a tick is late. Never behind `position`, never past the song's end.
    public func displayPosition(at date: Date = Date()) -> Double {
        guard phase == .playing else { return position }
        let ahead = min(max(date.timeIntervalSince(positionAnchor), 0), 2)
        let value = position + ahead
        return duration > 0 ? min(value, duration) : value
    }
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
    /// Match the output device's sample rate to each song (off by default: it changes the Mac's system output rate, which
    /// is put back when this is switched off and when the app quits).
    public var matchOutputRate: Bool {
        didSet {
            guard matchOutputRate != oldValue else { return }
            defaults.set(matchOutputRate, forKey: Self.matchRateKey)
            output.setMatchOutputRate(matchOutputRate)
        }
    }
    private static let matchRateKey = "discair.matchOutputRate"
    /// Called at quit.
    public func restoreOutputRate() { output.restoreOutputRate() }
    /// Streaming quality: nil is the original file, else a maximum in kbps from the stream allowlist. Applies to songs
    /// started afterwards (remembered).
    public var qualityCap: Int? {
        didSet {
            guard qualityCap != oldValue else { return }
            defaults.set(qualityCap ?? 0, forKey: Self.qualityKey)
            dropPreload(); refreshPreload()
        }
    }
    public static let qualityChoices: [Int?] = [nil, 320, 256, 192, 128, 96, 64]
    private static let qualityKey = "discair.qualityCap"
    /// Told to the owner when something was changed for them (an MP3 fallback); cleared when the next song starts.
    public internal(set) var notice: String?
    private static let crossfadeKey = "discair.crossfadeSeconds"
    /// App output level 0...1 (remembered).
    public var volume: Float {
        didSet { output.volume = volume; liveOutput.volume = volume; defaults.set(Double(volume), forKey: Self.volumeKey) }
    }
    /// The equalizer (remembered). Change it through `updateEQ`.
    public private(set) var eq = EQSettings()
    /// Report plays to Navidrome (per device, on by default). It feeds the listening history that discovery reads.
    public var scrobbling: Bool {
        didSet { defaults.set(scrobbling, forKey: Self.scrobbleKey); scrobbler.isEnabled = scrobbling }
    }
    private static let scrobbleKey = "discair.scrobbling"
    @ObservationIgnored let scrobbler: ScrobbleCoordinator
    private static let volumeKey = "discair.volume"
    private static let eqKey = "discair.equalizer"
    private static let queueKey = "discair.queue"
    public static let positionKey = "discair.queuePosition"
    public var current: QueueItem? { queue.current }

    // MARK: Waveform (contract section 7)

    /// 1000 peaks (0...1) for the playing song, or nil: the seek bar is then plain. Always the server's peaks, never a local decode.
    public private(set) var waveform: [Float]?
    /// Asks the Librarian for a song's peaks. Wired by `AppState`; the default has no server, so the bar stays plain.
    @ObservationIgnored public var waveformFetch: @Sendable (String) async -> SongPeaks = { _ in .unavailable }
    @ObservationIgnored public let waveformCache: WaveformCache
    /// How long to wait between asks while the server is still decoding the song, and how many times to ask.
    @ObservationIgnored var waveformRetry: Duration = .seconds(5)
    @ObservationIgnored var waveformAttempts = 12
    @ObservationIgnored private var waveformFor: UUID?
    @ObservationIgnored private var waveformTask: Task<Void, Never>?

    /// Called on every tick; does something only when the song changed.
    private func syncWaveform() {
        let item = queue.current
        guard item?.id != waveformFor else { return }
        waveformFor = item?.id
        waveformTask?.cancel(); waveformTask = nil
        waveform = nil
        guard let item else { return }
        if let cached = waveformCache.peaks(songID: item.songID) { waveform = cached; return }
        let id = item.id, songID = item.songID, cache = waveformCache
        waveformTask = Task { [weak self] in
            for attempt in 0..<(self?.waveformAttempts ?? 0) {
                guard let self, !Task.isCancelled, self.waveformFor == id else { return }
                switch await self.waveformFetch(songID) {
                case .ready(let peaks):
                    guard !Task.isCancelled, self.waveformFor == id else { return }
                    cache.put(peaks, songID: songID)
                    self.waveform = peaks
                    return
                case .unavailable: return
                case .pending:
                    if attempt + 1 < self.waveformAttempts { try? await Task.sleep(for: self.waveformRetry) }
                }
            }
        }
    }
    public var isPlaying: Bool { phase == .playing }
    public var shuffle: Bool { queue.shuffle }
    public var repeatMode: RepeatMode { queue.repeatMode }
    /// 0...1 for the progress bars.
    public var fraction: Double { duration > 0 ? min(max(position / duration, 0), 1) : 0 }

    @ObservationIgnored private var urls: StreamURLBuilder?
    @ObservationIgnored let output: AudioOutput

    // MARK: Live radio (stage 2, S2-2; rules in docs/RADIO_PLAYBACK_PROPOSAL.md S2.6)

    /// The station that is playing, or nil. Never saved with the queue.
    public internal(set) var live: LiveSession?
    /// The station that was stopped last, so Play can start it again. Cleared when a library song starts.
    @ObservationIgnored var stoppedStation: RadioStation?
    /// The playing station as the server sent it, for Next and Previous.
    @ObservationIgnored var stationByLive: RadioStation?
    @ObservationIgnored let liveOutput: LiveOutput
    /// Resolves a station's `playable_url` (the Librarian's relay path is relative). Set from the active profile.
    @ObservationIgnored var liveBase: URL?
    /// The favourites in server order, for station Next and Previous. Wired by `AppState`.
    @ObservationIgnored public var favouriteStations: () -> [RadioStation] = { [] }
    public static let lastStationKey = "discair.radio.lastStation"
    @ObservationIgnored private let fetcher: AudioFetcher
    @ObservationIgnored var loadTask: Task<Void, Never>?
    @ObservationIgnored private var tickTask: Task<Void, Never>?
    @ObservationIgnored var loadGeneration = 0
    @ObservationIgnored private var downloaded: URL?
    /// The current song while it streams to disk (contract 12.2); cancelled when the song changes.
    @ObservationIgnored private var growing: GrowingDownload?
    /// The message for a song whose download broke while it played; shown now and again after the next song starts.
    @ObservationIgnored private var cutShort: String?
    @ObservationIgnored let defaults: UserDefaults
    @ObservationIgnored private var preloadTask: Task<Void, Never>?
    /// The song handed to the engine (or being fetched) as the follower, and its file once downloaded.
    @ObservationIgnored private var preloaded: (id: UUID, file: URL?)?

    public init(output: AudioOutput = EngineOutput(), fetcher: AudioFetcher = URLSessionFetcher(), defaults: UserDefaults = .standard,
                waveformCache: WaveformCache = WaveformCache(), liveOutput: LiveOutput = LiveStreamPlayer()) {
        self.liveOutput = liveOutput
        self.waveformCache = waveformCache
        self.output = output
        self.fetcher = fetcher
        self.defaults = defaults
        let scrobbling = defaults.object(forKey: Self.scrobbleKey) as? Bool ?? true
        self.scrobbling = scrobbling
        scrobbler = ScrobbleCoordinator(enabled: scrobbling)
        let matchRate = defaults.bool(forKey: Self.matchRateKey)
        matchOutputRate = matchRate
        output.setMatchOutputRate(matchRate)
        let saved = defaults.integer(forKey: Self.crossfadeKey)
        crossfadeSeconds = Self.crossfadeChoices.contains(saved) ? saved : 0
        let q = defaults.integer(forKey: Self.qualityKey)
        qualityCap = allowedBitRates.contains(q) ? q : nil
        let v = defaults.object(forKey: Self.volumeKey) as? Double
        volume = Float(min(max(v ?? 1, 0), 1))
        output.volume = volume
        liveOutput.volume = volume
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
        liveOutput.onState = { [weak self] state in self?.liveStateChanged(state) }
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

    /// Sends each skip to the feedback outbox, then flushes in the background. Playback does not wait for either.
    public func configureFeedback(_ outbox: FeedbackOutbox) {
        scrobbler.onSkip = { event in
            Task { await outbox.enqueue(event); await outbox.flush() }
        }
    }

    public func configure(urls: StreamURLBuilder?, scrobbler client: (any Scrobbling)? = nil) {
        self.urls = urls
        scrobbler.configure(client: client)
        if urls == nil { stop() }
    }

    // MARK: Starting

    /// Plays `songs` from `startAt`, replacing the queue.
    public func play(_ songs: [QueueItem], startAt: Int = 0) {
        leaveByOwner()
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

    /// Adds several songs at the end in order (Radio from this, a saved queue). With nothing queued the first one plays.
    public func addToQueue(_ songs: [QueueItem]) {
        guard !songs.isEmpty else { return }
        let wasEmpty = queue.isEmpty
        for s in songs { queue.append(s) }
        if wasEmpty { startCurrent() } else { refreshPreload(); persist() }
    }

    /// Called when a song starts and fewer than three songs remain in Up Next (Autoplay uses it to top up).
    @ObservationIgnored public var onUpNextLow: (@MainActor () -> Void)?

    // MARK: Controls

    public func togglePlayPause() {
        if togglePlayPauseLive() { return }
        switch phase {
        case .playing: output.pause(); phase = .paused; position = output.position; stopTicking(); persist()
        case .paused: output.play(); phase = .playing; startTicking()
        case .idle, .failed: if current != nil { startCurrent(resume: true) }
        case .loading: break
        }
    }

    public func next() {
        if live != nil { stepStation(by: 1); return }
        leaveByOwner()
        pushHistory()
        guard queue.advance(natural: false) != nil else { stop(); return }
        startCurrent()
    }

    /// Past three seconds, Previous restarts the song; otherwise it goes back one.
    public func previous() {
        if live != nil { stepStation(by: -1); return }
        if phase == .playing || phase == .paused, output.position > 3 { seek(toSeconds: 0); return }
        let before = queue.current?.id, lastInQueue = queue.upNext.isEmpty
        guard queue.back() != nil else { return }
        // At the first song Previous only restarts it, which is not leaving it.
        if queue.current?.id != before { scrobbler.end(leftByOwner: true, wasLastInQueue: lastInQueue) }
        if !history.isEmpty { history.removeFirst() }
        startCurrent()
    }

    public func seek(toFraction f: Double) { seek(toSeconds: duration * min(max(f, 0), 1)) }

    public func seek(toSeconds s: Double) {
        guard live == nil, phase == .playing || phase == .paused else { return }
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
        if queue.upNext.indices.contains(i) { leaveByOwner() }
        pushHistory()
        queue.jump(upNext: i)
        startCurrent()
    }

    /// Plays a song that has already played (it stays in the queue, above the current song).
    public func jump(toPlayed i: Int) {
        guard queue.played.indices.contains(i) else { return }
        leaveByOwner()
        pushHistory()
        queue.jump(played: i)
        startCurrent()
    }

    /// Empties Up Next; the current song keeps playing.
    public func clearUpNext() { queue.clearUpNext(); refreshPreload(); persist() }

    public func stop() {
        endLive()
        loadGeneration += 1
        loadTask?.cancel()
        dropPreload()
        output.stop()
        stopTicking()
        phase = .idle; position = 0; duration = 0; resumeAt = 0
        scrobbler.end()
        cleanUp()
    }

    // MARK: Loading

    /// What to ask Navidrome for. Vorbis and WMA files go through the server as opus at 192 (owner decision, contract 12.8).
    /// With a quality cap, every song is asked for at most that bit rate (the server converts only when the file is above
    /// it); Vorbis and WMA go as opus at the lower of 192 and the cap.
    static func streamOptions(suffix: String?, cap: Int? = nil) -> (format: TranscodeFormat?, bitRate: Int?) {
        switch (suffix ?? "").lowercased() {
        case "ogg", "oga", "wma": (.opus, min(192, cap ?? 192))
        default: (nil, cap)
        }
    }

    /// `resume` is true only for Play on the queue restored at launch; every other start (a new album, Next, Previous, a
    /// jump) begins the song at 0, whatever place was saved.
    private func startCurrent(resume: Bool = false) {
        guard let item = queue.current else { stop(); return }
        guard let urls else { phase = .failed("Not connected to Navidrome. Check Settings."); return }
        endLive()
        stoppedStation = nil
        loadGeneration += 1
        let mine = loadGeneration
        loadTask?.cancel()
        dropPreload()
        output.stop(); stopTicking(); scrobbler.end()
        let startAt = resume ? resumeAt : 0; resumeAt = 0
        phase = .loading; position = startAt; duration = item.duration
        persist()
        if queue.upNext.count < 3 { onUpNextLow?() }
        notice = nil
        let cap = qualityCap
        var opts = Self.streamOptions(suffix: item.suffix, cap: cap)
        loadTask = Task { [weak self, fetcher] in
            do {
                // A progressive format starts while it downloads (contract 12.2). A cached song, or one the engine cannot
                // open while growing, takes the whole-file path below.
                let streamSuffix = opts.format?.rawValue ?? item.suffix
                let streamURL = try urls.streamURL(songID: item.songID, maxBitRate: opts.bitRate, format: opts.format)
                if ProgressiveStart.requiredBytes(suffix: streamSuffix) != nil, let download = fetcher.beginGrowing(streamURL, suffix: streamSuffix) {
                    do { try await Self.waitToStart(download, suffix: streamSuffix) }
                    catch { download.cancel(); try? FileManager.default.removeItem(at: download.file); throw error }
                    guard let self, !Task.isCancelled, self.loadGeneration == mine else { download.cancel(); try? FileManager.default.removeItem(at: download.file); return }
                    self.cleanUp()
                    self.growing = download
                    self.downloaded = download.file
                    if (try? self.output.openGrowing(download, expectedDuration: item.duration)) != nil {
                        self.startPlayback(item: item, startAt: startAt)
                        return
                    }
                    download.cancel()
                    self.growing = nil
                    self.downloaded = nil
                }
                var url = streamURL
                var file = try await fetcher.fetch(url, suffix: streamSuffix)
                guard let self, !Task.isCancelled, self.loadGeneration == mine else { try? FileManager.default.removeItem(at: file); return }
                self.cleanUp()
                self.downloaded = file
                do { try self.output.open(file: file) }
                catch let e as AudioError where opts.format == nil && e.description.contains("could not be opened") {
                    // The Mac cannot decode this file: ask the server for an MP3 of it, once, and say so. The saved quality is unchanged.
                    try? FileManager.default.removeItem(at: file)
                    opts = (.mp3, cap ?? 320)
                    url = try urls.streamURL(songID: item.songID, maxBitRate: opts.bitRate, format: opts.format)
                    file = try await fetcher.fetch(url, suffix: "mp3")
                    guard !Task.isCancelled, self.loadGeneration == mine else { try? FileManager.default.removeItem(at: file); return }
                    self.downloaded = file
                    try self.output.open(file: file)
                    self.notice = "This file cannot be played as it is, so the server sent an MP3 of it."
                }
                self.startPlayback(item: item, startAt: startAt)
            } catch {
                guard let self, self.loadGeneration == mine else { return }
                self.scrobbler.end()
                self.phase = .failed((error as? AudioError)?.description ?? "The song could not be played.")
            }
        }
    }

    /// The engine holds the song: seek to the saved place, play, and start the clock, scrobbling and the next song.
    private func startPlayback(item: QueueItem, startAt: Double) {
        duration = output.duration
        if startAt > 3, startAt < duration - 3 { output.seek(to: startAt); position = startAt }
        output.play()
        phase = .playing
        scrobbler.begin(songID: item.songID, duration: item.duration, mbid: item.mbid)
        startTicking()
        refreshPreload()
    }

    /// Waits until the download has enough on disk to start (or is complete). Throws if the download fails or the task is cancelled.
    private static func waitToStart(_ download: GrowingDownload, suffix: String?) async throws {
        while true {
            if let message = download.failure { throw AudioError(message) }
            if ProgressiveStart.canStart(suffix: suffix, bytesOnDisk: download.bytesOnDisk, complete: download.isComplete) { return }
            try Task.checkCancellation()
            try await Task.sleep(for: .milliseconds(100))
        }
    }

    private func songEnded() {
        stopTicking()
        noteBrokenDownload()
        var cut = cutShort; cutShort = nil
        // Say so when a song ends well before its length, so an early end is never silent.
        if cut == nil, duration > 10, position > 0, position < duration - 5, let c = queue.current {
            cut = "“\(c.title)” ended at \(Self.clock(position)) of \(Self.clock(duration))."
        }
        pushHistory()
        if queue.advance(natural: true) != nil { startCurrent() }
        else { dropPreload(); phase = .idle; position = 0; scrobbler.end(); cleanUp() }
        if let cut { notice = cut }        // `startCurrent` clears the notice, so it is put back for the new song
    }

    /// A growing song whose download broke plays what arrived and then ends. Say so, instead of ending without a word.
    private func noteBrokenDownload() {
        guard cutShort == nil, let download = growing, !download.isComplete, download.failure != nil else { return }
        let title = queue.current?.title ?? "The song"
        cutShort = "“\(title)” stopped downloading, so it ended early."
        notice = cutShort
    }

    /// The owner moves off the current song (Next, Previous, a jump, or another list). Runs before the queue moves, because
    /// it needs to know whether anything is queued after the song.
    private func leaveByOwner() {
        scrobbler.end(leftByOwner: true, wasLastInQueue: queue.upNext.isEmpty)
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
        // A growing song has no fixed end yet, so the follower waits until it is fully scheduled (the ticker retries).
        guard !output.isGrowing else { return }
        guard phase == .playing || phase == .paused, let now = queue.current, let next = queue.peekNext, let urls else {
            if phase == .playing || phase == .paused { dropPreload() }
            return
        }
        if preloaded?.id == next.id { return }
        dropPreload()
        let transition = Self.transition(from: now, to: next, crossfade: crossfadeSeconds)
        let opts = Self.streamOptions(suffix: next.suffix, cap: qualityCap)
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
        if let c = queue.current { scrobbler.begin(songID: c.songID, duration: c.duration, mbid: c.mbid) }
        refreshPreload()
        persist()
    }

    private func cleanUp() {
        growing?.cancel(); growing = nil
        if let d = downloaded { try? FileManager.default.removeItem(at: d); downloaded = nil }
    }

    private func startTicking() {
        stopTicking()
        tickTask = Task { [weak self] in
            var n = 0
            while !Task.isCancelled {
                self?.position = self?.output.position ?? 0
                self?.noteBrokenDownload()
                self?.syncWaveform()
                if let self, !self.output.isGrowing, self.phase == .playing { self.refreshPreload() }
                if let self { self.scrobbler.update(position: self.output.position, playerDuration: self.output.duration, isPlaying: self.output.isPlaying) }
                n += 1
                if n % 20 == 0 { self?.persist() }
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    func stopTicking() { tickTask?.cancel(); tickTask = nil }
}

extension PlayerModel {
    static func item(_ s: NavidromeSong) -> QueueItem {
        QueueItem(songID: s.id, title: s.title, artist: s.artist ?? "Unknown artist", album: s.album ?? "", albumID: s.albumId,
                  coverArt: s.coverArt, duration: Double(s.duration ?? 0), suffix: s.suffix, track: s.track, disc: s.discNumber, path: s.path,
                  mbid: s.musicBrainzId, quality: LibraryModel.rowFormat(s))
    }

    /// Sample rows (no server id) cannot be played.
    static func item(_ r: SongRow) -> QueueItem? {
        guard let id = r.remoteID else { return nil }
        return QueueItem(songID: id, title: r.title, artist: r.artist, album: r.cover?.title ?? "", albumID: r.cover?.remoteID,
                         coverArt: r.cover?.coverArt, duration: r.seconds, suffix: r.suffix, track: r.track, disc: r.disc, path: r.path,
                         quality: r.format.isEmpty ? nil : r.format)
    }

    /// "3:12" style clock for a number of seconds.
    public static func clock(_ seconds: Double) -> String {
        let s = Int(max(0, seconds)); return "\(s / 60):" + String(format: "%02d", s % 60)
    }
}
