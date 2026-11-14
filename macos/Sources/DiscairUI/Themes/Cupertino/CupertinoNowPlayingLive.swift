import AppKit
import DiscairLibrarian
import SwiftUI

/// Now Playing while a station plays, mockup C1 "Song first" (docs/design/macos-radio/mockups.html; docs/RADIO_PLAYBACK_PROPOSAL.md
/// S2-3 item 3). Built like the song's Now Playing: on the left the cover when the server sent one for the song (it is in the
/// library), else the station's logo, 230 pt with a 12 pt radius; LIVE and "station · time", the title, the artist, then Download and
/// Favourite. On the right, where the lyrics are, "Heard on (station) tonight": this station's plays of the last 12 hours, newest
/// first, at most 8, each with its button, and the line that says when Download appears. Seeking, the waveform, lyrics, the flip
/// cover, the booklet and the disc do not apply to a stream. The Sleep button joins with S2-4.
struct CupertinoNowPlayingLive: View {
    let state: AppState
    let live: LiveSession

    @Environment(\.stationLogos) private var logos
    /// The cover of the song, or the station's logo until it arrives and when the song has none.
    @State private var art: NSImage?

    private var p: PlayerModel { state.player }
    private var station: RadioStation? { state.stations.stations.first { $0.id == live.stationID } }

    var body: some View {
        ZStack(alignment: .topLeading) {
            NowPlayingCloseControls(state: state)
            left.frame(width: 420).padding(.leading, 90).padding(.top, 90)
            right.frame(maxWidth: .infinity, alignment: .topLeading).padding(.leading, 640).padding(.trailing, 60).padding(.top, 90)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(alignment: .topLeading) { backdrop }
        .foregroundStyle(CU.onMedia)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator())
        .background(TwoFingerSwipeDown(maxX: 620) { state.closeNowPlaying() })
        .task(id: "\(live.stationID)|\(p.liveNow?.coverPath ?? "")|\(logos?.generation ?? 0)") { await loadArt() }
        .task(id: live.stationID) { await state.loadHeard() }        // on opening Now Playing for radio (S2.5)
    }

    // MARK: Pictures

    private func loadArt() async {
        guard let logos else { art = nil; return }
        if let path = p.liveNow?.coverPath, !path.isEmpty, let cover = await logos.cover(path: path) { art = cover; return }
        art = await logos.logo(station: live.stationID, size: .large)
    }

    /// The dark plate of a station, with its picture blurred over it (mockup `.np::before`, which stands in for blurred artwork).
    private var backdrop: some View {
        ZStack {
            CU.playerGround
            LiveStationPlate.gradient
            if let art { Image(nsImage: art).resizable().scaledToFill().blur(radius: 70).opacity(0.5).clipped() }
            CU.shadowInk.opacity(0.28)
        }
        .accessibilityHidden(true)
    }

    private var cover: some View {
        let shape = RoundedRectangle(cornerRadius: 12, style: .continuous)
        return shape.fill(CU.onMedia.opacity(0.14))
            .overlay { if let art { Image(nsImage: art).resizable().scaledToFill() } }
            .clipShape(shape)
            .frame(width: 230, height: 230)
            .shadow(color: CU.shadowInk.opacity(0.5), radius: 35, y: 30)
            .accessibilityHidden(true)
    }

    // MARK: Left: the song

    private var left: some View {
        let line = p.liveLine
        let download = state.radioDownloads.state(now: p.liveNow)
        return VStack(alignment: .leading, spacing: 12) {
            cover
            HStack(spacing: 8) {
                LiveBadge()
                SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in
                    Text("\(live.name) · \(live.elapsedText(at: tl.date))").cuRole(CU.Font.callout).monospacedDigit()
                        .foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(1)
                }
            }
            .padding(.top, 12)
            .accessibilityElement(children: .combine)
            Text(line.headline(station: live.name)).font(CU.Font.title1.weighted(.bold)).lineLimit(2)
            if live.phaseSentence != nil {
                LivePhaseText(live: live).font(CU.Font.title2.weighted(.regular)).foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(2).padding(.top, -4)
            } else if let second = secondLine(line) {
                Text(second).font(CU.Font.title2.weighted(.regular)).foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(2).padding(.top, -4)
            }
            if line.sentence != nil, line.hasSong == false, let raw = line.title {
                Text(raw).font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.onMedia).lineLimit(2)      // an unmatched title is still worth showing
            }
            actions(download)
            if let sentence = state.radioDownloads.sentence(for: p.liveNow?.playID) {
                Text(sentence).cuRole(CU.Font.callout).foregroundStyle(CU.onMedia.opacity(0.85)).lineLimit(3)
            }
            transport
            HStack(spacing: 8) {
                Image(systemName: "speaker.fill").font(CU.Icon.small()).accessibilityHidden(true)
                DragBar(value: Double(p.volume), label: "Volume") { p.volume = Float($0) }
                Image(systemName: "speaker.wave.3.fill").font(CU.Icon.small()).accessibilityHidden(true)
            }
            .opacity(0.85).padding(.top, 4)
        }
        .accessibilityElement(children: .contain)
    }

    /// The artist for a song; else the state sentence ("This station sends no song titles."), or the connection phase.
    private func secondLine(_ line: LiveSongLine) -> String? {
        let text = line.hasSong ? line.detail : (line.sentence ?? "")
        return text.isEmpty ? nil : text
    }

    /// Download, Favourite and Sleep (Love was not chosen). The Download control is drawn only while a song can be
    /// asked for or its state is worth showing; a station with no titles shows its sentence instead.
    private func actions(_ download: DownloadState) -> some View {
        HStack(spacing: 8) {
            if download != .none, live.phase == .playing {
                SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in
                    DownloadButton(state: download, listeningSeconds: p.liveSongSince.map { DownloadState.listeningSeconds(since: $0, now: tl.date) }) {
                        if let id = p.liveNow?.playID { Task { await state.radioDownloads.get(playID: id) } }
                    }
                }
            }
            if let station {
                Button { Task { await state.stations.setFavourite(station, on: !station.favourite) } } label: {
                    HStack(spacing: 6) {
                        Image(systemName: station.favourite ? "star.fill" : "star")
                        Text("Favourite").cuRole(CU.Font.callout).fontWeight(.semibold)
                    }
                    .foregroundStyle(CU.onMedia).padding(.horizontal, 12).padding(.vertical, 4)
                    .background(CU.onMedia.opacity(0.18), in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(station.favourite ? "Favourite, on" : "Favourite, off")
            }
            SleepTimerMenu(timer: p.sleepTimer, style: .pill)
            if live.phase == .unreachable { RetryStationButton(player: p) }
        }
        .padding(.top, 4)
    }

    /// Previous station, Stop and next station. The bar is not shown on this screen, so Stop must be here.
    private var transport: some View {
        HStack(spacing: 34) {
            Button { p.previous() } label: { Image(systemName: "backward.fill").font(CU.Icon.transport()) }
                .accessibilityLabel("Previous station").disabled(state.stations.favourites.count < 2)
            Button { p.stopStation() } label: { Image(systemName: "stop.fill").font(CU.Icon.hero()) }
                .accessibilityLabel("Stop \(live.name)")
            Button { p.next() } label: { Image(systemName: "forward.fill").font(CU.Icon.transport()) }
                .accessibilityLabel("Next station").disabled(state.stations.favourites.count < 2)
        }
        .buttonStyle(.plain).frame(maxWidth: .infinity).padding(.top, 8)
    }

    // MARK: Right: heard tonight

    private var right: some View {
        let plays = HeardRules.tonight(on: live.name, in: state.radioPlays, at: Date(), excluding: p.liveNow?.playID)
        return VStack(alignment: .leading, spacing: 6) {
            Text("Heard on \(live.name) tonight").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.onMedia.opacity(0.7))
                .lineLimit(1).accessibilityAddTraits(.isHeader)
            if plays.isEmpty {
                Text("Nothing heard yet tonight.").cuRole(CU.Font.body).foregroundStyle(CU.onMedia.opacity(0.85))
            } else {
                HeardRows(plays: plays, state: state, surface: .media, showStation: false)
            }
            if let note = state.heardNote {
                Text(note).cuRole(CU.Font.callout).foregroundStyle(CU.onMedia).accessibilityLabel("Problem: \(note)")
            }
            Text(HeardRules.thresholdNote).cuRole(CU.Font.caption).foregroundStyle(CU.onMedia.opacity(0.75)).padding(.top, 6)
        }
        .frame(maxHeight: .infinity, alignment: .topLeading)
    }
}
