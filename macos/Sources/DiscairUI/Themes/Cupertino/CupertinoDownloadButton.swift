import SwiftUI

/// One Download control for every place a song is shown (S2-3 item 2; states and colours in S2.7). Words and a mark, never colour
/// alone. On the dark plate of a playing station (`.media`: the bar, the On Air panel, Now Playing) the ink is `onMedia`; on a page
/// (`.page`: the Heard tab and Home's rows) it uses the roles of the table. A state with no button (`.none`) draws nothing: the row
/// says why in its own sentence.
struct DownloadButton: View {
    enum Surface { case media, page }

    let state: DownloadState
    /// Seconds the Mac has heard this title, for "Listening · 12 s" while Download is not yet possible.
    var listeningSeconds: Int?
    var compact = false
    var surface: Surface = .media
    let action: () -> Void

    /// The brighter green of the dark plate (mockup `.np .btn.done`); the page roles are for light and dark pages.
    private static let plateGreen = Color(red: 0.35, green: 0.86, blue: 0.59)

    var body: some View {
        if let label = state.label(listeningSeconds: listeningSeconds) {
            Button(action: action) {
                HStack(spacing: 6) {
                    if state == .waiting { ring }
                    Text(label).cuRole(compact ? CU.Font.caption : CU.Font.callout).fontWeight(.semibold).monospacedDigit()
                }
                .foregroundStyle(ink)
                .padding(.horizontal, compact ? 8 : 12).padding(.vertical, compact ? 2 : 4)
                .background(fill, in: Capsule())
                .overlay { if state == .owned { Capsule().strokeBorder(outline, lineWidth: 1) } }
            }
            .buttonStyle(.plain)
            .disabled(!state.isEnabled)
            .accessibilityLabel(Self.spoken(state))
        }
    }

    /// A small ring that fills as the 30 seconds pass (mockup `.ring`).
    private var ring: some View {
        let progress = Double(min(max(listeningSeconds ?? 0, 0), 30)) / 30
        return ZStack {
            Circle().stroke(ink.opacity(0.3), lineWidth: 2)
            Circle().trim(from: 0, to: max(progress, 0.05)).stroke(ink, style: StrokeStyle(lineWidth: 2, lineCap: .butt)).rotationEffect(.degrees(-90))
        }
        .frame(width: 11, height: 11).accessibilityHidden(true)
    }

    private var ink: Color {
        switch (surface, state) {
        case (.media, .ready), (.media, .failed): CU.accentStrong
        case (.media, _): CU.onMedia
        case (.page, .ready), (.page, .failed): CU.onAccent
        case (.page, .working): CU.warning
        case (.page, .done): CU.success
        case (.page, _): CU.textSecondary
        }
    }

    private var fill: Color {
        switch (surface, state) {
        case (.media, .ready), (.media, .failed): CU.onMedia
        case (.media, .done): Self.plateGreen.opacity(0.25)
        case (.media, .owned): .clear
        case (.media, _): CU.onMedia.opacity(0.18)
        case (.page, .ready), (.page, .failed): CU.accent
        case (.page, .working): CU.warningTint
        case (.page, .done): CU.successTint
        case (.page, .owned): .clear
        case (.page, _): CU.bgFill
        }
    }

    private var outline: Color { surface == .media ? CU.onMedia.opacity(0.35) : CU.separator }

    /// What VoiceOver reads for each state.
    static func spoken(_ state: DownloadState) -> String {
        switch state {
        case .waiting: "Download, available once the song has been heard for about 30 seconds"
        case .ready: "Download this song"
        case .working: "Downloading"
        case .done: "Downloaded"
        case .owned: "Owned, already in your library"
        case .failed: "Try again"
        case .none: ""
        }
    }
}

/// The playing station's song and its Download control: the song, the artist or state sentence, the button and the server's
/// sentence beside it. Used by the On Air panel; the bar draws the same parts in one row.
struct LiveSongBlock: View {
    let player: PlayerModel
    let downloads: RadioDownloads

    var body: some View {
        let line = player.liveLine
        let state = downloads.state(now: player.liveNow)
        VStack(alignment: .leading, spacing: 4) {
            if let song = line.hasSong ? line.title : nil {
                Text(song).cuRole(CU.Font.body).fontWeight(.semibold).foregroundStyle(CU.onMedia).lineLimit(2)
            }
            let second = line.hasSong ? line.detail : (line.sentence ?? "")
            if !second.isEmpty { Text(second).cuRole(CU.Font.callout).foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(2) }
            if line.sentence != nil, let raw = line.title {      // an unmatched title is still worth showing
                Text(raw).cuRole(CU.Font.callout).foregroundStyle(CU.onMedia).lineLimit(2)
            }
            if state != .none {
                HStack(spacing: 8) {
                    SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in
                        DownloadButton(state: state, listeningSeconds: player.liveSongSince.map { DownloadState.listeningSeconds(since: $0, now: tl.date) }) {
                            if let id = player.liveNow?.playID { Task { await downloads.get(playID: id) } }
                        }
                    }
                    if let sentence = downloads.sentence(for: player.liveNow?.playID) {
                        Text(sentence).cuRole(CU.Font.caption).foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(2)
                    }
                }
                .padding(.top, 2)
            }
        }
        .accessibilityElement(children: .contain)
    }
}
