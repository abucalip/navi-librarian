import AppKit
import DiscairAudio
import DiscairLibrarian
import SwiftUI

/// What the mini window shows, worked out from the player. Pure so a test can check it without a window.
struct MiniPlayerContent: Equatable {
    var title: String
    var artist: String
    /// The next song in the queue (title and artist), or nil when nothing follows.
    var next: String?
    var hasSong: Bool
    /// A station plays (S2-2 item 7): the title is the station, the second line says "On air" or what is wrong, and there is no
    /// "next" line.
    var isLive = false

    init(current: QueueItem?, upNext: [QueueItem], live: LiveSession? = nil, liveNow: RadioNow? = nil) {
        if let live {
            isLive = true; hasSong = false
            let line = LiveSongLine.of(liveNow, phase: live.phase)
            // A song: its title over "Artist · Station". Otherwise the station over the state sentence.
            title = line.headline(station: live.name)
            artist = line.hasSong ? (line.artist.map { "\($0) · \(live.name)" } ?? live.name) : (line.sentence ?? "On air")
            next = nil
            return
        }
        hasSong = current != nil
        title = current?.title ?? "Nothing playing"
        artist = current?.artist ?? ""
        next = upNext.first.map { $0.artist.isEmpty ? $0.title : "\($0.title) · \($0.artist)" }
    }
}

/// The floating mini player (contract section 10): cover, transport, seek bar and a peek at the next track. It reads the
/// same `PlayerModel` as the main window, so the two never disagree. Dark in every theme because it sits over other apps;
/// the cover, blurred, is its backdrop.
public struct MiniPlayerView: View {
    @Bindable var state: AppState
    public static let size = CGSize(width: 340, height: 150)
    /// While a station plays the window is one row: logo, name and stop (mockup `.mini`).
    public static let liveSize = CGSize(width: 340, height: 76)

    public init(state: AppState) { self.state = state }

    private var p: PlayerModel { state.player }
    private var album: AlbumItem {
        guard let c = p.current else { return Fixtures.albums[0] }
        return AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true,
                         hue: LibraryModel.hue(for: c.album.isEmpty ? c.title : c.album), remoteID: c.albumID, coverArt: c.coverArt)
    }

    public var body: some View {
        let content = MiniPlayerContent(current: p.current, upNext: p.queue.upNext, live: p.live, liveNow: p.liveNow)
        if let live = p.live { liveBody(live, content) } else { songBody(content) }
    }

    /// Mockup `.mini`: the station logo at 52, then LIVE, the name and "On air", then a stop button. No seek bar, clock or
    /// "Next" line: none of them applies to a stream.
    private func liveBody(_ live: LiveSession, _ content: MiniPlayerContent) -> some View {
        let station = state.stations.stations.first { $0.id == live.stationID }
        return HStack(spacing: 12) {
            Group {
                if let station { StationLogo(station: station, size: 52, radiusFraction: 0.16) }
                else { RoundedRectangle(cornerRadius: 8, style: .continuous).fill(.white.opacity(0.1)).frame(width: 52, height: 52) }
            }
            VStack(alignment: .leading, spacing: 2) {
                Text("LIVE").font(.system(size: 10.5, weight: .bold)).tracking(0.8)
                    .foregroundStyle(Color(red: 0.70, green: 0.07, blue: 0.24))
                    .padding(.horizontal, 6).padding(.vertical, 1)
                    .background(.white, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
                    .accessibilityLabel("Live")
                Text(content.title).font(.system(size: 14, weight: .bold)).lineLimit(1)
                Text(content.artist).font(.system(size: 12)).foregroundStyle(.white.opacity(0.7)).lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            if live.phase == .unreachable {
                Button { p.retryStation() } label: {
                    Text("Retry").font(.system(size: 12, weight: .semibold)).foregroundStyle(Color(red: 0.70, green: 0.07, blue: 0.24))
                        .padding(.horizontal, 10).padding(.vertical, 4).background(.white, in: Capsule())
                }
                .buttonStyle(.plain).accessibilityLabel("Retry")
            }
            Button { p.stopStation() } label: {
                Image(systemName: "stop.fill").font(.system(size: 18, weight: .semibold)).frame(width: 36, height: 36)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Stop \(live.name)")
            .help("Stop")
        }
        .foregroundStyle(.white)
        .padding(12)
        .frame(width: Self.liveSize.width, height: Self.liveSize.height)
        .background(Color(red: 0.133, green: 0.125, blue: 0.165))
        .preferredColorScheme(.dark)
        .environment(\.artwork, state.artwork)
        .environment(\.stationLogos, state.stationLogos)
        .background(MiniWindowConfigurator())
    }

    private func songBody(_ content: MiniPlayerContent) -> some View {
        HStack(spacing: 12) {
            CoverView(album: album, px: 240)
                .frame(width: 96, height: 96)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            VStack(alignment: .leading, spacing: 4) {
                Text(content.title).font(.system(size: 14, weight: .bold)).lineLimit(1)
                Text(content.artist).font(.system(size: 12)).foregroundStyle(.white.opacity(0.7)).lineLimit(1)
                DragBar(value: p.fraction, height: 4, peaks: p.waveform, label: "Position",
                        valueText: { "\(PlayerModel.clock($0 * p.duration)) of \(PlayerModel.clock(p.duration))" }) { p.seek(toFraction: $0) }
                    .disabled(!content.hasSong)
                HStack(spacing: 0) {
                    control("backward.fill", "Previous") { p.previous() }
                    control(p.isPlaying ? "pause.fill" : "play.fill", p.isPlaying ? "Pause" : "Play", size: 20) { p.togglePlayPause() }
                    control("forward.fill", "Next") { p.next() }
                    Spacer(minLength: 0)
                    PlaybackClock(player: p) { Text(PlayerModel.clock($0)).font(.system(size: 11).monospacedDigit()).foregroundStyle(.white.opacity(0.6)) }
                }
                Text(content.next.map { "Next: \($0)" } ?? "Nothing queued next")
                    .font(.system(size: 11)).foregroundStyle(.white.opacity(0.55)).lineLimit(1)
                    .accessibilityLabel(content.next.map { "Next up: \($0)" } ?? "Nothing queued next")
            }
        }
        .foregroundStyle(.white)
        .padding(12)
        .frame(width: Self.size.width, height: Self.size.height)
        .background {
            ZStack {
                Color.black
                BlurredArtwork(album: album, radius: 24).opacity(0.55)
            }
        }
        .preferredColorScheme(.dark)
        .environment(\.artwork, state.artwork)
        .background(MiniWindowConfigurator())
    }

    private func control(_ symbol: String, _ label: String, size: CGFloat = 15, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol).font(.system(size: size, weight: .semibold)).frame(width: 36, height: 28)
        }
        .buttonStyle(.plain)
        .disabled(p.current == nil)
        .accessibilityLabel(label)
        .help(label)
    }
}

/// Makes the mini window float above other apps' windows, stay on every Space, and drag by its background.
struct MiniWindowConfigurator: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let v = NSView()
        DispatchQueue.main.async { Self.configure(v.window) }
        return v
    }
    func updateNSView(_ nsView: NSView, context: Context) {}
    @MainActor static func configure(_ w: NSWindow?) {
        guard let w else { return }
        w.level = .floating
        w.collectionBehavior.insert(.canJoinAllSpaces)
        w.collectionBehavior.insert(.fullScreenAuxiliary)
        w.isMovableByWindowBackground = true
        w.titlebarAppearsTransparent = true
        w.titleVisibility = .hidden
        w.styleMask.insert(.fullSizeContentView)
        w.styleMask.remove(.resizable)
        w.hidesOnDeactivate = false
    }
}
