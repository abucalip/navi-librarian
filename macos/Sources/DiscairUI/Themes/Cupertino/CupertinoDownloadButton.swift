import SwiftUI

/// One Download control for every place a live song is shown (S2-3 item 2; states in S2.7). Words and a mark, never colour alone.
/// It sits on the dark plate of a playing station, so the ink is `onMedia`. A state with no button (`.none`) draws nothing: the
/// row says why in its own sentence.
struct DownloadButton: View {
    let state: DownloadState
    /// Seconds the Mac has heard this title, for "Listening · 12 s" while Download is not yet possible.
    var listeningSeconds: Int?
    var compact = false
    let action: () -> Void

    var body: some View {
        if let label = state.label(listeningSeconds: listeningSeconds) {
            Button(action: action) {
                Text(label).cuRole(compact ? CU.Font.caption : CU.Font.callout).fontWeight(.semibold).monospacedDigit()
                    .foregroundStyle(state.isEnabled ? CU.accentStrong : CU.onMedia)
                    .padding(.horizontal, compact ? 8 : 12).padding(.vertical, compact ? 2 : 4)
                    .background(state.isEnabled ? CU.onMedia : CU.onMedia.opacity(0.2), in: Capsule())
                    .opacity(state == .waiting || state == .working ? 0.85 : 1)
            }
            .buttonStyle(.plain)
            .disabled(!state.isEnabled)
            .accessibilityLabel(Self.spoken(state))
        }
    }

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
