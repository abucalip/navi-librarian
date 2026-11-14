import DiscairLibrarian
import Foundation

/// What the player reads from `GET /api/radio/stations/{id}/now` while a station plays (S2-3 item 1).
public protocol LiveNowSource: Sendable {
    func radioNow(station: String) async throws -> RadioNow
}
extension LibrarianClient: LiveNowSource {}

/// The words and parts of the live song, pure so a test can drive them (docs/RADIO_PLAYBACK_CONTRACT.md section 6).
/// A song is shown only for the state `ok`; every other state is a sentence that takes the artist line's place.
struct LiveSongLine: Equatable {
    /// The song title, or the raw title a station sent that could not be split. Nil when no title is known.
    var title: String?
    var artist: String?
    /// The state sentence when no song can be shown; nil while a song is.
    var sentence: String?

    var hasSong: Bool { title != nil && sentence == nil }

    /// "Artist – Title", the title alone, or nil.
    var songText: String? {
        guard let title else { return nil }
        guard let artist else { return title }
        return "\(artist) – \(title)"
    }

    /// The bar's first line: the song, else the station.
    func headline(station: String) -> String { hasSong ? (title ?? station) : station }
    /// The bar's second line: the artist, else the state sentence.
    var detail: String { artist ?? sentence ?? "" }

    static let waiting = LiveSongLine(title: nil, artist: nil, sentence: "On air")

    /// `now` is nil until the first answer arrives.
    static func of(_ now: RadioNow?) -> LiveSongLine {
        guard let now else { return .waiting }
        switch now.state {
        case .ok:
            if let title = now.title { return LiveSongLine(title: title, artist: now.artist, sentence: nil) }
            if let raw = now.rawTitle { return LiveSongLine(title: raw, artist: nil, sentence: nil) }
            return LiveSongLine(title: nil, artist: nil, sentence: "This station sends no song titles.")
        case .unparsed:
            return LiveSongLine(title: now.rawTitle, artist: nil,
                                sentence: "The title could not be matched to an artist and song.")
        case .noMetadata, .unknown:
            return LiveSongLine(title: nil, artist: nil, sentence: "This station sends no song titles.")
        case .notProxied:
            return LiveSongLine(title: nil, artist: nil, sentence: "Not relayed · no song titles.")
        case .unavailable:
            return LiveSongLine(title: nil, artist: nil, sentence: "Station unreachable.")
        case .idle:
            return .waiting
        }
    }

    /// The line with the connection state in front of it: a station that is connecting, reconnecting or unreachable says so
    /// instead of a title that may be out of date.
    static func of(_ now: RadioNow?, phase: LiveSession.Phase) -> LiveSongLine {
        switch phase {
        case .playing: return of(now)
        case .connecting: return LiveSongLine(title: nil, artist: nil, sentence: "Connecting…")
        case .reconnecting: return LiveSongLine(title: nil, artist: nil, sentence: "Reconnecting…")
        case .unreachable: return LiveSongLine(title: nil, artist: nil, sentence: "Station unreachable")
        }
    }

    /// Changes when the song changes, so a Download attempt and the "listening" count belong to one title.
    static func key(_ now: RadioNow?) -> String? {
        guard let now, now.state == .ok else { return nil }
        let k = [now.artist, now.title, now.rawTitle].map { $0 ?? "" }.joined(separator: "|")
        return k == "||" ? nil : k
    }
}
