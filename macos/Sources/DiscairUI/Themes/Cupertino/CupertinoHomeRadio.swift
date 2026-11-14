import AppKit
import DiscairLibrarian
import SwiftUI

/// The radio card in Home's first row (E7; mockup "Small pieces", `.hcard`): a panel with the logo or the song's cover at 56 pt,
/// the text, and one or two buttons. The rule for what it shows is `HomeRadioCard`.
struct HomeRadioCardView: View {
    let state: AppState
    let card: HomeRadioCard

    @Environment(\.stationLogos) private var logos
    @State private var cover: NSImage?

    private var p: PlayerModel { state.player }

    var body: some View {
        HStack(spacing: 12) {
            picture
            VStack(alignment: .leading, spacing: 2) { text }
            Spacer(minLength: CU.Space.s)
            buttons
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .contain)
        .task(id: "\(p.liveNow?.coverPath ?? "")|\(logos?.generation ?? 0)") { await loadCover() }
    }

    private func loadCover() async {
        guard case .onAir = card, let logos, let path = p.liveNow?.coverPath, !path.isEmpty else { cover = nil; return }
        cover = await logos.cover(path: path)
    }

    @ViewBuilder private var picture: some View {
        switch card {
        case .onAir(let id, _, _):
            if let cover, p.liveNow?.coverPath?.isEmpty == false {
                Image(nsImage: cover).resizable().scaledToFill().frame(width: 56, height: 56)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous)).accessibilityHidden(true)
            } else if let station = state.stations.stations.first(where: { $0.id == id }) {
                StationLogo(station: station, size: 56)
            } else {
                RoundedRectangle(cornerRadius: 12, style: .continuous).fill(CU.bgFill).frame(width: 56, height: 56)
            }
        case .resume(let station, _):
            StationLogo(station: station, size: 56)
        }
    }

    @ViewBuilder private var text: some View {
        switch card {
        case .onAir(_, let name, let line):
            pageLiveBadge
            Text(line.hasSong ? (line.title ?? name) : name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
            Text(secondLine(line, station: name)).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
        case .resume(let station, let when):
            Text(station.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
            Text(when).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
        }
    }

    /// "Talk Talk · FIP" for a song; the state sentence ("Connecting…", "This station sends no song titles.") otherwise.
    private func secondLine(_ line: LiveSongLine, station: String) -> String {
        if line.hasSong { return [line.artist, station].compactMap { $0 }.joined(separator: " · ") }
        return line.sentence ?? station
    }

    /// LIVE on a page: the accent ground with the label colour on it (S2.7). The word, never a dot alone.
    private var pageLiveBadge: some View {
        Text("LIVE").font(CU.Font.caption.weighted(.bold)).tracking(0.8)
            .foregroundStyle(CU.onAccent)
            .padding(.horizontal, 6).padding(.vertical, 1)
            .background(CU.accent, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
            .accessibilityLabel("Live")
    }

    @ViewBuilder private var buttons: some View {
        switch card {
        case .onAir(_, let name, _):
            neutral("stop.fill", "Stop", label: "Stop \(name)") { p.stopStation() }
            neutral(nil, "Open Radio", label: "Open the Radio page") { state.screen = .stations }
        case .resume(let station, _):
            Button { p.playStation(station) } label: {
                HStack(spacing: 6) { Image(systemName: "play.fill"); Text("Resume").cuRole(CU.Font.callout) }
                    .foregroundStyle(CU.onAccent).padding(.horizontal, 12).padding(.vertical, 4)
                    .background(CU.accent, in: Capsule())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Resume \(station.name)")
        }
    }

    private func neutral(_ symbol: String?, _ title: String, label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let symbol { Image(systemName: symbol) }
                Text(title).cuRole(CU.Font.callout)
            }
            .foregroundStyle(CU.text).padding(.horizontal, 12).padding(.vertical, 4)
            .background(CU.bgFill, in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
