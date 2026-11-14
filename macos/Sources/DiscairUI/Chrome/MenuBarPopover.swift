import AppKit
import DiscairAudio
import DiscairLibrarian
import SwiftUI

/// The menu bar item's label (docs/RADIO_PLAYBACK_PROPOSAL.md S2-5 item 1): the `radio` symbol while a station plays, a note for a
/// library song, and the title cut at 30 characters while "Show title" is on. Reads `AppState` only.
public struct MenuBarLabel: View {
    let state: AppState
    let showTitle: Bool
    public init(state: AppState, showTitle: Bool) { self.state = state; self.showTitle = showTitle }

    private var content: MenuBarContent {
        MenuBarContent(live: state.player.live, liveNow: state.player.liveNow, current: state.player.current, showTitle: showTitle)
    }

    public var body: some View {
        let c = content
        HStack(spacing: 4) {
            Image(systemName: c.symbol)
            if let title = c.labelTitle { Text(title) }
        }
        .accessibilityLabel(c.spoken)
    }
}

/// The popover of mockup D2 (`.pop`, 300 pt): cover or logo, LIVE and the station (or album), the title and artist; Stop or
/// Play/Pause, Next for a library song, the shared Download button and the sleep timer; the first four favourites with their keys;
/// "Open Discair". It reads `AppState` only and makes no request of its own.
public struct MenuBarPopover: View {
    let state: AppState
    let showTitle: Bool
    let openApp: () -> Void
    @State private var art: NSImage?

    public init(state: AppState, showTitle: Bool, openApp: @escaping () -> Void) {
        self.state = state; self.showTitle = showTitle; self.openApp = openApp
    }

    private var p: PlayerModel { state.player }
    private var content: MenuBarContent {
        MenuBarContent(live: p.live, liveNow: p.liveNow, current: p.current, showTitle: showTitle)
    }

    public var body: some View {
        let c = content
        VStack(alignment: .leading, spacing: 8) {
            header(c)
            if c.kind != .idle { actions(c) }
            favourites
            Divider()
            Button(action: openApp) {
                Text("Open Discair").cuRole(CU.Font.body).foregroundStyle(CU.text)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 6).padding(.vertical, 4).contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .frame(width: 300)
        .preferredColorScheme(state.appearance.mode == .night ? .dark : .light)
        .environment(\.artwork, state.artwork)
        .environment(\.stationLogos, state.stationLogos)
        .accessibilityElement(children: .contain)
    }

    // MARK: Cover, words

    private func header(_ c: MenuBarContent) -> some View {
        HStack(spacing: 10) {
            cover(c)
            VStack(alignment: .leading, spacing: 1) {
                if c.kind == .station {
                    HStack(spacing: 6) {
                        Text("LIVE").font(CU.Font.caption.weighted(.bold)).tracking(0.8).foregroundStyle(CU.onAccent)
                            .padding(.horizontal, 6).padding(.vertical, 1)
                            .background(CU.accent, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
                            .accessibilityLabel("Live")
                        Text(c.caption).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                    }
                } else if !c.caption.isEmpty {
                    Text(c.caption).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                }
                Text(c.headline).font(CU.Font.body.weighted(.bold)).foregroundStyle(CU.text).lineLimit(1)
                if !c.detail.isEmpty {
                    if c.kind == .station, let live = p.live, live.phase == .reconnecting, live.reconnect != nil {
                        LivePhaseText(live: live, role: CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                    } else {
                        Text(c.detail).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement(children: .combine)
        .task(id: "\(p.live?.stationID ?? "")|\(p.liveNow?.coverPath ?? "")") { await loadArt() }
    }

    @ViewBuilder private func cover(_ c: MenuBarContent) -> some View {
        let shape = RoundedRectangle(cornerRadius: 8, style: .continuous)
        if c.kind == .song {
            CoverView(album: MiniPlayerView.album(for: p.current), px: 160)
                .frame(width: 54, height: 54).clipShape(shape).accessibilityHidden(true)
        } else {
            shape.fill(CU.bgFill)
                .overlay { if c.kind == .station, let art { Image(nsImage: art).resizable().scaledToFill() }
                           else { Image(systemName: "music.note").foregroundStyle(CU.textTertiary) } }
                .clipShape(shape).frame(width: 54, height: 54).accessibilityHidden(true)
        }
    }

    /// The song's cover when the server found one, else the station's logo (read through the shared logo store).
    private func loadArt() async {
        guard let live = p.live else { art = nil; return }
        let logos = state.stationLogos
        if let path = p.liveNow?.coverPath, !path.isEmpty, let cover = await logos.cover(path: path) { art = cover; return }
        art = await logos.logo(station: live.stationID, size: .small)
    }

    // MARK: Buttons

    private func actions(_ c: MenuBarContent) -> some View {
        HStack(spacing: 8) {
            if c.showsStop { pill("stop.fill", "Stop", spoken: "Stop \(p.live?.name ?? "radio")") { p.stopStation() } }
            if c.showsPlayPause {
                pill(p.isPlaying ? "pause.fill" : "play.fill", p.isPlaying ? "Pause" : "Play") { p.togglePlayPause() }
            }
            if c.showsNext { pill("forward.fill", "Next") { p.next() } }
            if c.showsRetry {
                Button { p.retryStation() } label: {
                    Text("Retry").cuRole(CU.Font.callout).fontWeight(.semibold).lineLimit(1).fixedSize()
                        .foregroundStyle(CU.onAccent).padding(.horizontal, 12).padding(.vertical, 4).background(CU.accent, in: Capsule())
                }
                .buttonStyle(.plain).accessibilityLabel("Retry")
            }
            if c.showsDownload { download }
            SleepTimerMenu(timer: p.sleepTimer, style: .neutral)
            Spacer(minLength: 0)
        }
    }

    @ViewBuilder private var download: some View {
        let download = state.radioDownloads.state(now: p.liveNow)
        if download != .none {
            SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in
                DownloadButton(state: download, listeningSeconds: p.liveSongSince.map { DownloadState.listeningSeconds(since: $0, now: tl.date) },
                               compact: true, surface: .page) {
                    if let id = p.liveNow?.playID { Task { await state.radioDownloads.get(playID: id) } }
                }
            }
        }
    }

    private func pill(_ symbol: String, _ title: String, spoken: String? = nil, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: symbol)
                Text(title).cuRole(CU.Font.callout).fontWeight(.semibold)
            }
            .foregroundStyle(CU.text).padding(.horizontal, 12).padding(.vertical, 4).background(CU.bgFill, in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(spoken ?? title)
    }

    // MARK: Favourites

    @ViewBuilder private var favourites: some View {
        let list = Array(StationRules.shortcutStations(state.stations.stations).prefix(MenuBarContent.favouriteCount))
        if !list.isEmpty {
            Divider()
            VStack(spacing: 0) {
                ForEach(Array(list.enumerated()), id: \.element.id) { i, station in
                    Button { state.tuneShortcut(i + 1) } label: {
                        HStack(spacing: 10) {
                            StationLogo(station: station, size: 26)
                            Text(station.name).cuRole(CU.Font.body).foregroundStyle(CU.text).lineLimit(1).frame(maxWidth: .infinity, alignment: .leading)
                            Text("⌘\(i + 1)").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                        }
                        .padding(.horizontal, 6).padding(.vertical, 4).contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Play \(station.name), Command \(i + 1)")
                }
            }
        }
    }
}
