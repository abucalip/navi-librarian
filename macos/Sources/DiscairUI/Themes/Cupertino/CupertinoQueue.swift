import DiscairAudio
import SwiftUI

/// Queue: Up Next as a trailing inspector (glass, a control layer) over the Albums grid, with an Autoplay (radio)
/// switch, saved queue and history. Mockup: `R.cupertino.queue`.
struct CupertinoAlbumsGrid: View {
    let state: AppState
    /// True when the Up Next inspector is open and the grid must stay clear of it.
    var inspector = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Albums").font(CU.title(34)).padding(.top, 4).padding(.bottom, 14)
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.muted).padding(.bottom, 8) }
                if case .failed(let m) = state.library.phase { Text(m).foregroundStyle(CU.accent).padding(.bottom, 8) }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 18, alignment: .top)], alignment: .leading, spacing: 18) {
                    ForEach(state.library.albums) { a in
                        Button { state.selectedAlbum = a; state.screen = .album } label: {
                        VStack(alignment: .leading, spacing: 0) {
                            CoverView(album: a).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                .shadow(color: .black.opacity(0.2), radius: 7, y: 4).padding(.bottom, 9)
                            Text(a.title).fontWeight(.semibold).lineLimit(1)
                            Text(a.artist).foregroundStyle(CU.muted).lineLimit(1)
                        }
                        .font(.system(size: 13)).frame(width: 128, alignment: .leading)
                        .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(a.title), \(a.artist)")
                    }
                }
            }
            .padding(.leading, 28).padding(.trailing, 28 + (inspector ? CupertinoQueueInspector.width : 0)).padding(.bottom, 28)   // keeps content out from under the inspector
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}

struct CupertinoQueueInspector: View {
    let state: AppState
    static let width: CGFloat = 380
    @State private var showHistory = false
    @State private var autoplay = true

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                segmented
                Spacer()
                Text(live ? liveSummary : "8 songs · 52 min").foregroundStyle(CU.muted).font(.system(size: 13))
            }
            .padding(.bottom, 12)

            if !live {
            HStack(spacing: 10) {
                Image(systemName: "dot.radiowaves.left.and.right").font(.system(size: 16))
                VStack(alignment: .leading, spacing: 1) {
                    Text("Autoplay").fontWeight(.semibold)
                    Text("Radio from this, similar artists by Librarian").font(.system(size: 12)).foregroundStyle(CU.muted)
                }
                Spacer(minLength: 4)
                Toggle("Autoplay", isOn: $autoplay).labelsHidden().toggleStyle(.switch).tint(.green)
            }
            .padding(.horizontal, 8).padding(.top, 8).padding(.bottom, 12)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.ink.opacity(0.08)).frame(height: 1) }
            .padding(.bottom, 8)
            }

            ScrollView {
                VStack(spacing: 0) {
                    if live { liveRows }
                    else if showHistory {
                        Text("Earlier today: Glory Box · Roygbiv · Cloudbusting").foregroundStyle(CU.muted).padding(8)
                    } else {
                        ForEach(Array(Fixtures.queue.enumerated()), id: \.offset) { i, q in row(i, q) }
                    }
                }
            }
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                if !live { Button("Save queue") { }.buttonStyle(CapsuleButtonStyle()) }
                Button("Clear") { if live { state.player.clearUpNext() } }.buttonStyle(CapsuleButtonStyle())
                    .disabled(live && state.player.queue.upNext.isEmpty)
            }
            .padding(.top, 10)
        }
        .font(.system(size: 13))
        .padding(.top, 66).padding([.horizontal, .bottom], 18)
        .frame(width: Self.width).frame(maxHeight: .infinity)
        .glassEffect(CU.glass, in: Rectangle())
        .overlay(alignment: .leading) { Rectangle().fill(CU.ink.opacity(0.08)).frame(width: 1) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Up Next")
    }

    private var live: Bool { state.library.isLive || state.player.current != nil }

    private var liveSummary: String {
        let p = state.player
        let up = p.queue.upNext
        let minutes = Int(up.reduce(0) { $0 + $1.duration } / 60)
        return up.isEmpty ? "Nothing queued" : "\(up.count) up next · \(minutes) min"
    }

    @ViewBuilder private var liveRows: some View {
        let p = state.player
        if showHistory {
            if p.history.isEmpty { Text("Nothing played yet this session.").foregroundStyle(CU.muted).padding(8) }
            ForEach(p.history) { h in songRow(h, time: PlayerModel.clock(h.duration), playing: false) }
        } else {
            if let c = p.current { songRow(c, time: PlayerModel.clock(c.duration), playing: true) }
            else { Text("Nothing playing. Play a song and what follows shows here.").foregroundStyle(CU.muted).padding(8) }
            let up = p.queue.upNext
            ForEach(Array(up.enumerated()), id: \.element.id) { i, item in
                songRow(item, time: PlayerModel.clock(item.duration), playing: false) {
                    Menu {
                        Button("Play now") { p.jump(toUpNext: i) }
                        Button("Move up") { p.moveUpNext(from: i, to: i - 1) }.disabled(i == 0)
                        Button("Move down") { p.moveUpNext(from: i, to: i + 1) }.disabled(i == up.count - 1)
                        Divider()
                        Button("Remove from queue", role: .destructive) { p.removeUpNext(at: i) }
                    } label: { Image(systemName: "ellipsis.circle") }
                    .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
                    .accessibilityLabel("Actions for \(item.title)")
                }
            }
        }
    }

    private func songRow<T: View>(_ q: QueueItem, time: String, playing: Bool, @ViewBuilder trailing: () -> T = { EmptyView() }) -> some View {
        HStack(spacing: 11) {
            CoverView(album: AlbumItem(id: -1, title: q.album, artist: q.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: q.coverArt))
                .frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous)).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(q.artist).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            HStack(spacing: 4) {
                if playing { Image(systemName: "waveform").accessibilityLabel("Playing") }
                Text(time).monospacedDigit()
            }
            .font(.system(size: 12)).foregroundStyle(CU.muted)
            trailing()
        }
        .padding(.horizontal, 8).padding(.vertical, 6)
        .background(playing ? CU.accent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
        .accessibilityElement(children: .combine)
    }

    private var segmented: some View {
        HStack(spacing: 0) {
            seg("Up Next", on: !showHistory) { showHistory = false }
            seg("History", on: showHistory) { showHistory = true }
        }
        .padding(3).background(Color(red: 0.47, green: 0.47, blue: 0.5).opacity(0.14), in: Capsule())
    }

    private func seg(_ t: String, on: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).font(.system(size: 13, weight: on ? .semibold : .medium)).padding(.horizontal, 14).padding(.vertical, 3)
                .background(on ? Color.white : .clear, in: Capsule())
                .shadow(color: .black.opacity(on ? 0.15 : 0), radius: 1.5, y: 1)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private func row(_ i: Int, _ q: (title: String, album: Int, time: String)) -> some View {
        let a = Fixtures.albums[q.album]
        return HStack(spacing: 11) {
            CoverView(album: a).frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(a.artist).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            HStack(spacing: 4) {
                if i == 0 { Image(systemName: "waveform").accessibilityLabel("Playing") }
                Text(q.time).monospacedDigit()
            }
            .font(.system(size: 12)).foregroundStyle(CU.muted)
        }
        .padding(.horizontal, 8).padding(.vertical, 6)
        .background(i == 0 ? CU.accent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
        .accessibilityElement(children: .combine)
    }
}
