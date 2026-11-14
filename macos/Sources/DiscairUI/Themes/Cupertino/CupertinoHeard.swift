import DiscairLibrarian
import SwiftUI

/// One heard song: title over "Artist · 21:09", its Download control, and the server's sentence once it has answered (kept on the
/// row). Mockup `hrow`. Used by the On Air panel and Now Playing (on the plate, `.media`) and by the Heard tab (on the page).
struct HeardRow: View {
    let play: RadioPlay
    let state: AppState
    var surface: DownloadButton.Surface = .page
    /// False where the list is one station's own ("Heard on FIP tonight"): the station's name is left out.
    var showStation = true

    private var downloads: RadioDownloads { state.radioDownloads }
    private var ink: Color { surface == .media ? CU.onMedia : CU.text }
    private var secondary: Color { surface == .media ? CU.onMedia.opacity(0.72) : CU.textSecondary }

    var body: some View {
        let download = state.downloadState(playID: play.id)
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(play.title).cuRole(CU.Font.headline).foregroundStyle(ink).lineLimit(1)
                    Text(HeardRules.detail(play, showStation: showStation)).cuRole(CU.Font.callout).foregroundStyle(secondary).lineLimit(1)
                }
                Spacer(minLength: CU.Space.s)
                DownloadButton(state: download, compact: surface == .media, surface: surface) { Task { await downloads.get(playID: play.id) } }
            }
            if let sentence = downloads.sentence(for: play.id) {
                Text(sentence).cuRole(CU.Font.caption).foregroundStyle(download == .failed && surface == .page ? CU.danger : secondary).lineLimit(2)
            }
        }
        .padding(.vertical, 6)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(HeardRules.spoken(play, showStation: showStation))
    }
}

/// The rows of a station's recent plays with a rule between them (mockup `.row + .row`). `rule` is the rule's colour.
struct HeardRows: View {
    let plays: [RadioPlay]
    let state: AppState
    var surface: DownloadButton.Surface = .media
    var showStation = false

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(plays.enumerated()), id: \.element.id) { i, play in
                if i > 0 { Rectangle().fill(surface == .media ? CU.onMedia.opacity(0.14) : CU.separator).frame(height: 1) }
                HeardRow(play: play, state: state, surface: surface, showStation: showStation)
            }
        }
    }
}

/// "Heard on (station)" under the On Air hero (mockup A2): the last three plays of the playing station and "All heard songs ›", which
/// switches the page to the Heard tab. Nothing shows until the station has a heard song.
struct OnAirHeard: View {
    let state: AppState
    let live: LiveSession

    var body: some View {
        let plays = HeardRules.latest(on: live.name, in: state.radioPlays, excluding: state.player.liveNow?.playID)
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("Heard on \(live.name)").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary).lineLimit(1)
            if plays.isEmpty {
                Text("Nothing heard yet on this station.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            } else {
                HeardRows(plays: plays, state: state, surface: .page, showStation: false)
            }
            if state.stations.pane != .heard {
                Button { state.stations.pane = .heard } label: {
                    Text("All heard songs ›").cuRole(CU.Font.callout).fontWeight(.semibold).foregroundStyle(CU.accent)
                }
                .buttonStyle(.plain).accessibilityLabel("All heard songs")
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

/// The Heard tab: every play, newest first, grouped by day, each with its station, time and Download control.
struct HeardList: View {
    let state: AppState

    var body: some View {
        let days = HeardRules.grouped(state.radioPlays, at: Date())
        VStack(alignment: .leading, spacing: CU.Space.m) {
            if let note = state.heardNote {
                Text(note).cuRole(CU.Font.callout).foregroundStyle(CU.danger).accessibilityLabel("Problem: \(note)")
            }
            if days.isEmpty {
                Text(HeardRules.emptyText).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
            } else {
                ForEach(days) { day in
                    VStack(alignment: .leading, spacing: CU.Space.xs) {
                        Text(day.title).cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                            .accessibilityAddTraits(.isHeader)
                        HeardRows(plays: day.plays, state: state, surface: .page, showStation: true)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
    }
}
