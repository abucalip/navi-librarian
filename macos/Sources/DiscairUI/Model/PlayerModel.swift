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

    public init(output: AudioOutput = EngineOutput(), fetcher: AudioFetcher = URLSessionFetcher()) {
        self.output = output
        self.fetcher = fetcher
        output.onFinished = { [weak self] in self?.songEnded() }
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
        if wasEmpty { startCurrent() }
    }

    public func addToQueue(_ song: QueueItem) {
        let wasEmpty = queue.isEmpty
        queue.append(song)
        if wasEmpty { startCurrent() }
    }

    // MARK: Controls

    public func togglePlayPause() {
        switch phase {
        case .playing: output.pause(); phase = .paused; position = output.position; stopTicking()
        case .paused: output.play(); phase = .playing; startTicking()
        case .idle, .failed: if current != nil { startCurrent() }
        case .loading: break
        }
    }

    public func next() {
        guard queue.advance(natural: false) != nil else { stop(); return }
        startCurrent()
    }

    /// Past three seconds, Previous restarts the song; otherwise it goes back one.
    public func previous() {
        if phase == .playing || phase == .paused, output.position > 3 { seek(toSeconds: 0); return }
        guard queue.back() != nil else { return }
        startCurrent()
    }

    public func seek(toFraction f: Double) { seek(toSeconds: duration * min(max(f, 0), 1)) }

    public func seek(toSeconds s: Double) {
        guard phase == .playing || phase == .paused else { return }
        output.seek(to: s)
        position = output.position
    }

    public func toggleShuffle() { queue.setShuffle(!queue.shuffle) }

    public func cycleRepeat() {
        queue.repeatMode = switch queue.repeatMode { case .off: .all; case .all: .one; case .one: .off }
    }

    public func removeUpNext(at i: Int) { queue.removeUpNext(at: i) }
    public func moveUpNext(from: Int, to: Int) { queue.moveUpNext(from: from, to: to) }

    public func stop() {
        loadGeneration += 1
        loadTask?.cancel()
        output.stop()
        stopTicking()
        phase = .idle; position = 0; duration = 0
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
        output.stop(); stopTicking()
        phase = .loading; position = 0; duration = item.duration
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
                self.output.play()
                self.phase = .playing
                self.startTicking()
            } catch {
                guard let self, self.loadGeneration == mine else { return }
                self.phase = .failed((error as? AudioError)?.description ?? "The song could not be played.")
            }
        }
    }

    private func songEnded() {
        stopTicking()
        if queue.advance(natural: true) != nil { startCurrent() }
        else { phase = .idle; position = 0; cleanUp() }
    }

    private func cleanUp() {
        if let d = downloaded { try? FileManager.default.removeItem(at: d); downloaded = nil }
    }

    private func startTicking() {
        stopTicking()
        tickTask = Task { [weak self] in
            while !Task.isCancelled {
                self?.position = self?.output.position ?? 0
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    private func stopTicking() { tickTask?.cancel(); tickTask = nil }
}

extension PlayerModel {
    static func item(_ s: NavidromeSong) -> QueueItem {
        QueueItem(songID: s.id, title: s.title, artist: s.artist ?? "Unknown artist", album: s.album ?? "", albumID: s.albumId,
                  coverArt: s.coverArt, duration: Double(s.duration ?? 0), suffix: s.suffix)
    }

    /// Sample rows (no server id) cannot be played.
    static func item(_ r: SongRow) -> QueueItem? {
        guard let id = r.remoteID else { return nil }
        return QueueItem(songID: id, title: r.title, artist: r.artist, album: r.cover?.title ?? "", albumID: r.cover?.remoteID,
                         coverArt: r.cover?.coverArt, duration: r.seconds, suffix: r.suffix)
    }

    /// "3:12" style clock for a number of seconds.
    public static func clock(_ seconds: Double) -> String {
        let s = Int(max(0, seconds)); return "\(s / 60):" + String(format: "%02d", s % 60)
    }
}
