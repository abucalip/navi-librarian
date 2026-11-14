import DiscairAudio
import DiscairLibrarian
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

    /// The time since tuning in as the bar and the On Air panel show it: "19:12", or "1:02:03" after an hour. Never negative.
    public func elapsedText(at now: Date) -> String {
        let total = max(0, Int(now.timeIntervalSince(startedAt)))
        let h = total / 3600, m = (total % 3600) / 60, s = total % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, m, s) : String(format: "%d:%02d", m, s)
    }

    /// A sentence for a phase that is not plain playing, or nil while the station plays. No address is ever in it.
    public var phaseSentence: String? {
        switch phase {
        case .playing: nil
        case .connecting: "Connecting…"
        case .reconnecting: "Reconnecting…"
        case .unreachable: "Station unreachable"
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
        liveOutput.start(url: url)
        onNowPlayingChange?()
    }

    /// Stops the station. The queue stays paused on the same song.
    public func stopStation() {
        guard let station = stationByLive else { return }
        endLive()
        stoppedStation = station
    }

    /// Tears the station down without remembering it for Play (a library song starts, or the app disconnects).
    func endLive() {
        guard live != nil else { return }
        liveOutput.stop()
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

    func liveStateChanged(_ state: LiveState) {
        guard live != nil else { return }
        live?.phase = switch state {
        case .connecting: .connecting
        case .playing: .playing
        case .stalled: .reconnecting
        case .failed: .unreachable
        }
        onNowPlayingChange?()
    }

    private func pauseLibrarySongForStation() {
        output.pause()
        phase = .paused
        position = output.position
        stopTicking()
        persist()
    }
}
