import DiscairLibrarian
import Foundation

/// The Heard list's rules, pure so a test can drive them (docs/RADIO_PLAYBACK_PROPOSAL.md S2-3 items 3 to 5). The list is the
/// server's `GET /api/radio/plays`, newest first; nothing here reads the network or the clock (it is passed in).
enum HeardRules {
    /// "Heard on (station) tonight": the last 12 hours, at most 8 rows (Now Playing).
    static let tonightHours = 12
    static let tonightLimit = 8
    /// The On Air panel lists the last three plays of the playing station.
    static let panelLimit = 3

    static let emptyText = "Songs you hear for 30 seconds on a relayed station are listed here."
    static let thresholdNote = "Download appears once a song has been heard for about 30 seconds."

    /// A play carries the station's name, not its id, so the match is on the name (trimmed, case-insensitive).
    static func isOn(_ play: RadioPlay, station name: String) -> Bool {
        play.stationName.trimmingCharacters(in: .whitespacesAndNewlines)
            .caseInsensitiveCompare(name.trimmingCharacters(in: .whitespacesAndNewlines)) == .orderedSame
    }

    /// This station's plays, newest first. `excluding` leaves out the song that is on now (it has its own place on the page).
    static func plays(on station: String, in plays: [RadioPlay], excluding playID: Int? = nil) -> [RadioPlay] {
        plays.filter { isOn($0, station: station) && $0.id != playID }.sorted { $0.heardAt > $1.heardAt }
    }

    /// Now Playing's right column: this station's plays of the last 12 hours, newest first, at most 8.
    static func tonight(on station: String, in plays: [RadioPlay], at now: Date, excluding playID: Int? = nil) -> [RadioPlay] {
        let cutoff = now.addingTimeInterval(-Double(tonightHours) * 3600).timeIntervalSince1970
        return Array(self.plays(on: station, in: plays, excluding: playID).filter { $0.heardAt >= cutoff }.prefix(tonightLimit))
    }

    /// The On Air panel's three rows.
    static func latest(on station: String, in plays: [RadioPlay], excluding playID: Int? = nil) -> [RadioPlay] {
        Array(self.plays(on: station, in: plays, excluding: playID).prefix(panelLimit))
    }

    /// One day of the Heard tab.
    struct Day: Equatable, Identifiable {
        let title: String
        let plays: [RadioPlay]
        var id: String { title }
    }

    /// Every play, newest first, under "Today", "Yesterday" or the date. Whole calendar days, not 24-hour spans.
    static func grouped(_ plays: [RadioPlay], at now: Date, calendar: Calendar = .current) -> [Day] {
        var days: [Day] = []
        for play in plays.sorted(by: { $0.heardAt > $1.heardAt }) {
            let title = dayTitle(Date(timeIntervalSince1970: play.heardAt), at: now, calendar: calendar)
            if let last = days.last, last.title == title { days[days.count - 1] = Day(title: title, plays: last.plays + [play]) }
            else { days.append(Day(title: title, plays: [play])) }
        }
        return days
    }

    static func dayTitle(_ date: Date, at now: Date, calendar: Calendar = .current) -> String {
        let days = calendar.dateComponents([.day], from: calendar.startOfDay(for: date), to: calendar.startOfDay(for: now)).day ?? 0
        switch days {
        case ..<1: return "Today"
        case 1: return "Yesterday"
        default:
            let f = DateFormatter()
            f.calendar = calendar; f.timeZone = calendar.timeZone; f.locale = Locale(identifier: "en_US_POSIX")
            f.dateFormat = "EEEE d MMMM"
            return f.string(from: date)
        }
    }

    /// "21:14".
    static func timeText(_ play: RadioPlay, calendar: Calendar = .current) -> String {
        let c = calendar.dateComponents([.hour, .minute], from: Date(timeIntervalSince1970: play.heardAt))
        return String(format: "%02d:%02d", c.hour ?? 0, c.minute ?? 0)
    }

    /// The line under a row's title: "Radiohead · 21:09" on a station's own list, "Radiohead · FIP · 21:09" where stations mix.
    static func detail(_ play: RadioPlay, showStation: Bool, calendar: Calendar = .current) -> String {
        var parts: [String] = []
        if let artist = play.artist, !artist.isEmpty { parts.append(artist) }
        if showStation, !play.stationName.isEmpty { parts.append(play.stationName) }
        parts.append(timeText(play, calendar: calendar))
        return parts.joined(separator: " · ")
    }

    /// What VoiceOver reads for a row.
    static func spoken(_ play: RadioPlay, showStation: Bool, calendar: Calendar = .current) -> String {
        "\(play.title), \(detail(play, showStation: showStation, calendar: calendar))"
    }
}
