import DiscairAudio
import DiscairLibrarian
import Foundation
import Observation

/// The menu bar item's switches, kept in `UserDefaults` (docs/RADIO_PLAYBACK_PROPOSAL.md S2-5 item 3). Both are on by default.
public enum MenuBarSettings {
    public static let showKey = "discair.menubar.show"
    public static let showTitleKey = "discair.menubar.showTitle"
}

/// What the menu bar item says and which buttons its popover shows (S2-5 items 1 and 2; mockup D2), worked out from the player.
/// Pure so a test can check it without a menu bar.
struct MenuBarContent: Equatable {
    enum Kind: Equatable { case station, song, idle }

    /// The title in the menu bar is cut at this many characters, the cut mark included.
    static let titleLimit = 30
    /// How many favourites the popover lists (the first four, with their keys).
    static let favouriteCount = 4

    var kind: Kind
    /// SF Symbol of the label: `radio` for a station, a note for a library song (also when nothing plays).
    var symbol: String
    /// The text beside the symbol, already cut; nil when "Show title" is off or there is nothing to say.
    var labelTitle: String?
    /// The small line over the title: the station for radio, the album for a library song; empty when there is none.
    var caption: String
    var headline: String
    var detail: String
    /// Stop (radio) or Play/Pause (a library song) and Next (a library song only; a station has no next).
    var showsStop: Bool
    var showsPlayPause: Bool
    var showsNext: Bool
    /// Download is offered for radio only, while the station plays; the view still hides it when the song has no state.
    var showsDownload: Bool
    var showsRetry: Bool

    init(live: LiveSession?, liveNow: RadioNow?, current: QueueItem?, showTitle: Bool) {
        if let live {
            kind = .station
            symbol = "radio"
            let line = LiveSongLine.of(liveNow, phase: live.phase)
            headline = line.headline(station: live.name)
            detail = live.phaseSentence ?? (line.hasSong ? (line.artist ?? "") : (line.sentence ?? "On air"))
            caption = live.name
            labelTitle = showTitle ? Self.cut(line.hasSong ? (line.songText.map { $0.replacingOccurrences(of: " – ", with: " — ") } ?? live.name) : live.name) : nil
            showsStop = true; showsPlayPause = false; showsNext = false
            showsDownload = live.phase == .playing
            showsRetry = live.phase == .unreachable
        } else if let current {
            kind = .song
            symbol = "music.note"
            headline = current.title
            detail = current.artist
            caption = current.album
            let text = current.artist.isEmpty ? current.title : "\(current.artist) — \(current.title)"
            labelTitle = showTitle ? Self.cut(text) : nil
            showsStop = false; showsPlayPause = true; showsNext = true
            showsDownload = false; showsRetry = false
        } else {
            kind = .idle
            symbol = "music.note"
            headline = "Nothing playing"; detail = ""; caption = ""
            labelTitle = nil
            showsStop = false; showsPlayPause = false; showsNext = false
            showsDownload = false; showsRetry = false
        }
    }

    /// The text cut to `titleLimit` characters, ending in an ellipsis; shorter text is left alone.
    static func cut(_ text: String) -> String {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard t.count > titleLimit else { return t }
        return String(t.prefix(titleLimit - 1)).trimmingCharacters(in: .whitespaces) + "…"
    }

    /// What VoiceOver reads for the item.
    var spoken: String {
        switch kind {
        case .station: "Discair, \(caption) on air, \(headline)"
        case .song: "Discair, \(headline)\(detail.isEmpty ? "" : " by \(detail)")"
        case .idle: "Discair, nothing playing"
        }
    }
}

/// Whether the menu bar item is inserted, as a plain observable value for the `MenuBarExtra` scene.
///
/// The scene must not take a binding made by `@AppStorage` on the `App` struct: SwiftUI writes `isInserted` back while it sets the
/// scene up, the write invalidates the `App` body, and the main thread then loops at full CPU with memory growing, so the app
/// never finishes starting. This object writes `UserDefaults` only when the value really changes, and follows changes made
/// elsewhere (the Settings > Radio switch is an `@AppStorage` on the same key).
@MainActor @Observable
public final class MenuBarVisibility {
    public var isInserted: Bool {
        didSet { if isInserted != Self.stored(defaults) { defaults.set(isInserted, forKey: MenuBarSettings.showKey) } }
    }
    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored nonisolated(unsafe) private var observer: (any NSObjectProtocol)?

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        isInserted = Self.stored(defaults)
        observer = NotificationCenter.default.addObserver(forName: UserDefaults.didChangeNotification, object: defaults, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.refresh() }
        }
    }

    deinit { if let observer { NotificationCenter.default.removeObserver(observer) } }

    /// Takes over a change made through the defaults. Equal values are ignored, so nothing loops.
    func refresh() {
        let value = Self.stored(defaults)
        if value != isInserted { isInserted = value }
    }

    /// On unless switched off (a missing value means on).
    static func stored(_ defaults: UserDefaults) -> Bool { defaults.object(forKey: MenuBarSettings.showKey) as? Bool ?? true }
}
