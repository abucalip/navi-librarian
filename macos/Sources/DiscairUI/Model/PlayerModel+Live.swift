import DiscairAudio
import DiscairLibrarian
import AppKit
import Foundation

/// A station that is playing (stage 2, S2-2 item 3). The queue is not touched by it and nothing here is saved with the queue.
public struct LiveSession: Equatable, Sendable {
    public enum Phase: Equatable, Sendable { case connecting, playing, reconnecting, unreachable }
    public let stationID: String
    public let name: String
    public let logoPath: String
    /// When the owner tuned in; the bar shows the time since.
    public let startedAt: Date
    public var phase: Phase
    /// While a try to reconnect is waiting or under way (S2-4 item 1); nil otherwise.
    public var reconnect: Reconnect?

    /// The try that is waiting or running: its number, the count of tries, and when it starts.
    public struct Reconnect: Equatable, Sendable {
        public var attempt: Int
        public var of: Int
        public var retryAt: Date
    }

    /// The time since tuning in as the bar and the On Air panel show it: "19:12", or "1:02:03" after an hour. Never negative.
    public func elapsedText(at now: Date) -> String {
        let total = max(0, Int(now.timeIntervalSince(startedAt)))
        let h = total / 3600, m = (total % 3600) / 60, s = total % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, m, s) : String(format: "%d:%02d", m, s)
    }

    /// A sentence for a phase that is not plain playing, or nil while the station plays. No address is ever in it.
    public var phaseSentence: String? { phaseSentence(at: Date()) }

    /// The same at a moment, so a view that ticks shows the countdown: "Connection lost · trying again in 5 s (attempt 2 of 5)"
    /// while a try waits, "Reconnecting… (attempt 2 of 5)" while it runs, "Reconnecting…" for a stall that has not been given up on.
    public func phaseSentence(at now: Date) -> String? {
        switch phase {
        case .playing: return nil
        case .connecting: return "Connecting…"
        case .unreachable: return "Station unreachable"
        case .reconnecting:
            guard let r = reconnect else { return "Reconnecting…" }
            let wait = Int(r.retryAt.timeIntervalSince(now).rounded(.up))
            if wait > 0 { return "Connection lost · trying again in \(wait) s (attempt \(r.attempt) of \(r.of))" }
            return "Reconnecting… (attempt \(r.attempt) of \(r.of))"
        }
    }
}

extension PlayerModel {
    /// The sentence for a station whose address is a playlist the Mac cannot read, or nil when it can be played.
    static func playlistRefusal(for station: RadioStation) -> String? {
        guard !station.proxied else { return nil }
        let path = (URL(string: station.playableURL)?.path ?? station.playableURL).lowercased()
        guard path.hasSuffix(".pls") || path.hasSuffix(".m3u") else { return nil }
        return "This station's address is a playlist the Mac cannot play. Switch its relay on from the web Radio page."
    }

    /// Starts a station. A library song that was playing is paused and the queue stays as it is.
    public func playStation(_ station: RadioStation) {
        if let refusal = Self.playlistRefusal(for: station) { notice = refusal; return }
        guard let url = URL(string: station.playableURL, relativeTo: liveBase)?.absoluteURL, url.scheme?.hasPrefix("http") == true else {
            notice = "This station cannot be played."; return
        }
        notice = nil
        loadTask?.cancel(); loadGeneration += 1
        if phase == .playing || phase == .loading { pauseLibrarySongForStation() }
        restoreOutputRate()
        stoppedStation = nil
        live = LiveSession(stationID: station.id, name: station.name, logoPath: station.logoPath, startedAt: Date(), phase: .connecting)
        stationByLive = station
        defaults.set(station.id, forKey: Self.lastStationKey)
        liveURL = url
        reconnectPolicy.reset()
        liveOutput.start(url: url)
        armSilenceWatchdog()
        startLiveNowPolling(for: station)
        onNowPlayingChange?()
    }

    /// Stops the station. The queue stays paused on the same song.
    public func stopStation() {
        guard let station = stationByLive else { return }
        endLive()
        stoppedStation = station
        sleepTimer.cancel()
    }

    /// Tears the station down without remembering it for Play (a library song starts, or the app disconnects).
    func endLive() {
        guard live != nil else { return }
        cancelReconnectWork()
        liveURL = nil
        liveOutput.stop()
        stopLiveNowPolling()
        live = nil
        stationByLive = nil
        onNowPlayingChange?()
    }

    /// Play/Pause while a station is chosen: stops the station, or starts the stopped one again. False when no station is involved.
    func togglePlayPauseLive() -> Bool {
        if live != nil { stopStation(); return true }
        if let station = stoppedStation { playStation(station); return true }
        return false
    }

    /// Next and Previous on a station go to the following or preceding favourite in server order, wrapping. With fewer than
    /// two favourites nothing happens. A station that is not a favourite goes to the first (Next) or last (Previous) favourite.
    func stepStation(by delta: Int) {
        let favourites = favouriteStations()
        guard favourites.count >= 2 else { return }
        let index = favourites.firstIndex { $0.id == live?.stationID }
        let target: Int
        if let index { target = (index + delta + favourites.count) % favourites.count }
        else { target = delta > 0 ? 0 : favourites.count - 1 }
        playStation(favourites[target])
    }

    // MARK: The live song (S2-3 item 1)

    /// Reads the station's song every 5 s while it plays. A station that is not relayed has no title, so nothing is asked.
    private func startLiveNowPolling(for station: RadioStation) {
        stopLiveNowPolling()
        if !station.proxied { applyLiveNow(RadioNow(state: .notProxied), for: station.id); return }
        guard liveNowSource != nil else { return }
        liveNowTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                await self.pollLiveNow()
                await self.liveNowPause(Self.liveNowInterval)
            }
        }
    }

    private func stopLiveNowPolling() {
        liveNowTask?.cancel(); liveNowTask = nil
        liveNow = nil; liveSongKey = nil; liveSongSince = nil
    }

    /// One read. A failed read keeps what was shown; an answer for a station that is no longer playing is dropped. Public so a
    /// test can drive it without the timer.
    public func pollLiveNow() async {
        guard let id = live?.stationID, stationByLive?.proxied == true, let source = liveNowSource else { return }
        guard let answer = try? await source.radioNow(station: id) else { return }
        applyLiveNow(answer, for: id)
    }

    private func applyLiveNow(_ answer: RadioNow, for stationID: String) {
        guard live?.stationID == stationID, answer != liveNow else { return }
        let key = LiveSongLine.key(answer)
        if key != liveSongKey { liveSongKey = key; liveSongSince = key == nil ? nil : Date() }
        let newPlay = answer.playID != nil && answer.playID != liveNow?.playID
        liveNow = answer
        onNowPlayingChange?()
        if newPlay { onLivePlay?() }
    }

    /// The line the bar, the panel, the mini player and the system show for the playing station.
    var liveLine: LiveSongLine { LiveSongLine.of(liveNow, phase: live?.phase ?? .playing) }

    func liveStateChanged(_ state: LiveState) {
        guard live != nil, !systemAsleep else { return }
        switch state {
        case .playing:
            reconnectPolicy.sound()
            cancelReconnectWork()
            live?.phase = .playing
            live?.reconnect = nil
        case .connecting:
            // A try in flight keeps its "Reconnecting…" words; a first connection says "Connecting…".
            if live?.reconnect == nil { live?.phase = .connecting }
        case .stalled:
            live?.phase = .reconnecting
            armSilenceWatchdog()
        case .failed:
            streamDropped()
        }
        onNowPlayingChange?()
    }

    // MARK: Reconnect (S2-4 item 1; rules in `ReconnectPolicy`)

    /// A drop, an error status, or 20 s without sound. Asks the policy for the next step; nothing is tried once the owner has
    /// stopped (`live` is nil then) or while the Mac sleeps.
    func streamDropped() {
        guard live != nil, !systemAsleep else { return }
        cancelReconnectWork()
        switch reconnectPolicy.drop() {
        case .giveUp:
            liveOutput.stop()
            live?.phase = .unreachable
            live?.reconnect = nil
        case .retry(let delay, let attempt):
            liveOutput.stop()
            live?.phase = .reconnecting
            live?.reconnect = LiveSession.Reconnect(attempt: attempt, of: ReconnectPolicy.attempts, retryAt: Date().addingTimeInterval(delay))
            let id = live?.stationID
            reconnectTask = Task { [weak self] in
                guard let self else { return }
                await self.reconnectPause(delay)
                guard !Task.isCancelled, self.live?.stationID == id, !self.systemAsleep, let url = self.liveURL else { return }
                self.liveOutput.start(url: url)
                self.armSilenceWatchdog()
                self.onNowPlayingChange?()
            }
        }
        onNowPlayingChange?()
    }

    /// 20 s of connecting or buffering without sound counts as a drop. Sound or a new drop cancels it.
    func armSilenceWatchdog() {
        silenceTask?.cancel()
        silenceTask = Task { [weak self] in
            guard let self else { return }
            await self.reconnectPause(ReconnectPolicy.silenceLimit)
            guard !Task.isCancelled, self.live != nil, self.live?.phase != .playing, self.live?.phase != .unreachable else { return }
            self.streamDropped()
        }
    }

    func cancelReconnectWork() {
        reconnectTask?.cancel(); reconnectTask = nil
        silenceTask?.cancel(); silenceTask = nil
    }

    /// Retry on "Station unreachable": a fresh round, at once.
    public func retryStation() {
        guard live?.phase == .unreachable, let url = liveURL else { return }
        freshRound(url: url)
    }

    private func freshRound(url: URL) {
        cancelReconnectWork()
        reconnectPolicy.reset()
        live?.phase = .connecting
        live?.reconnect = nil
        liveOutput.stop()
        liveOutput.start(url: url)
        armSilenceWatchdog()
        onNowPlayingChange?()
    }

    // MARK: The Mac sleeping (S2-4 item 1)

    /// While the Mac sleeps nothing is tried.
    public func systemWillSleep() {
        systemAsleep = true
        cancelReconnectWork()
        if live != nil { liveOutput.stop() }
    }

    /// On wake, one fresh round if a station was playing (including one that had been given up on).
    public func systemDidWake() {
        systemAsleep = false
        guard live != nil, let url = liveURL else { return }
        freshRound(url: url)
    }

    /// Watches the Mac going to sleep and waking. Called once by `AppState`.
    public func observeSystemSleep() {
        guard sleepObservers.isEmpty else { return }
        let center = NSWorkspace.shared.notificationCenter
        sleepObservers = [
            center.addObserver(forName: NSWorkspace.willSleepNotification, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.systemWillSleep() }
            },
            center.addObserver(forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.systemDidWake() }
            },
        ]
    }

    // MARK: The sleep timer (S2-4 item 2)

    /// Time is up: a station stops (and can be started again with Play), a library song pauses.
    func sleepTimerExpired() {
        if live != nil { stopStation() }
        else if phase == .playing { togglePlayPause() }
        else if phase == .loading { stop() }
    }

    private func pauseLibrarySongForStation() {
        output.pause()
        phase = .paused
        position = output.position
        stopTicking()
        persist()
    }
}
