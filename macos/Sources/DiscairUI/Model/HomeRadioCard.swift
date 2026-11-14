import DiscairLibrarian
import Foundation

/// The radio card in Home's first row (E7, S2-3 item 6; mockup "Small pieces", `.hcard`). Pure, so a test can drive all three cases.
///  - A station plays: its logo (or the song's cover), LIVE, the song or the state sentence, the station, Stop and Open Radio.
///  - None plays, a last station is known and still in the list: its logo, name, "Last played …" and Resume.
///  - Otherwise no card.
enum HomeRadioCard: Equatable {
    case onAir(stationID: String, name: String, line: LiveSongLine)
    case resume(station: RadioStation, lastPlayed: String)

    static func of(live: LiveSession?, line: LiveSongLine, lastStationID: String?, stations: [RadioStation],
                   at date: Date, calendar: Calendar = .current) -> HomeRadioCard? {
        if let live { return .onAir(stationID: live.stationID, name: live.name, line: line) }
        guard let lastStationID, let station = stations.first(where: { $0.id == lastStationID }) else { return nil }
        return .resume(station: station, lastPlayed: lastPlayedText(station.lastPlayedAt, at: date, calendar: calendar))
    }

    /// "Last played today, 21:17", "Last played yesterday", "Last played 3 days ago"; "Never played" when the server has no time.
    static func lastPlayedText(_ lastPlayedAt: Double?, at date: Date, calendar: Calendar = .current) -> String {
        let text = StationRules.playedText(lastPlayedAt, at: date, calendar: calendar)
        return text.hasPrefix("Played ") ? "Last played " + text.dropFirst("Played ".count) : text
    }

    /// The line under the song title: "Artist · Station", or the state sentence with the station. The title is the first line.
    var stationName: String {
        switch self { case .onAir(_, let name, _): name; case .resume(let s, _): s.name }
    }
}
