import DiscairAudio
import SwiftUI

/// Queue: Up Next as a trailing inspector (glass, a control layer) over the Albums grid, with an Autoplay (radio)
/// switch, saved queue and history. Mockup: `R.cupertino.queue`.
struct CupertinoAlbumsGrid: View {
    let state: AppState
    /// The Recently Added tab: the newest albums instead of the alphabetical grid.
    var recent = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text(recent ? "Recently Added" : "Albums").font(CU.title(34)).padding(.top, 4).padding(.bottom, 14)
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.muted).padding(.bottom, 8) }
                if case .failed(let m) = state.library.phase { Text(m).foregroundStyle(CU.accent).padding(.bottom, 8) }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 18, alignment: .top)], alignment: .leading, spacing: 18) {
                    ForEach(state.visible(recent ? state.library.recent : state.library.albums)) { a in
                        Button { state.open(album: a) } label: {
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
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}

struct CupertinoQueueInspector: View {
    let state: AppState
    static let width: CGFloat = 380
    private enum Tab { case upNext, history, saved }
    @State private var tab = Tab.upNext
    @State private var saving = false
    @State private var saveName = ""
    private var showHistory: Bool { tab == .history }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                segmented
                Spacer()
                Text(tab == .saved ? "\(state.savedQueues.queues.count) saved" : live ? liveSummary : "8 songs · 52 min").foregroundStyle(CU.muted).font(.system(size: 13)).lineLimit(1).minimumScaleFactor(0.8)
            }
            .padding(.bottom, 12)

            HStack(spacing: 10) {
                Image(systemName: "dot.radiowaves.left.and.right").font(.system(size: 16))
                VStack(alignment: .leading, spacing: 1) {
                    Text("Autoplay").fontWeight(.semibold)
                    Text(state.radio.status ?? "Radio from this, similar artists in your library").font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(2)
                }
                Spacer(minLength: 4)
                Button("Radio") { state.startRadio() }.buttonStyle(CapsuleButtonStyle())
                    .disabled(state.radio.busy || state.player.current == nil)
                    .accessibilityLabel("Start radio from this song")
                if state.radio.sonicAvailable {
                    Button("Sounds like") { state.startSonicRadio() }.buttonStyle(CapsuleButtonStyle())
                        .disabled(state.radio.busy || state.player.current == nil)
                        .accessibilityLabel("Add songs that sound like this song")
                }
                Toggle("Autoplay", isOn: Bindable(state.radio).autoplay).labelsHidden().toggleStyle(.switch).tint(.green)
            }
            .padding(.horizontal, 8).padding(.top, 8).padding(.bottom, 12)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.ink.opacity(0.08)).frame(height: 1) }
            .padding(.bottom, 8)

            ScrollView {
                VStack(spacing: 0) {
                    if tab == .saved { savedRows }
                    else if live { liveRows }
                    else if showHistory {
                        Text("Earlier today: Glory Box · Roygbiv · Cloudbusting").foregroundStyle(CU.muted).padding(8)
                    } else {
                        ForEach(Array(Fixtures.queue.enumerated()), id: \.offset) { i, q in row(i, q) }
                    }
                }
            }
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                if saving {
                    TextField("Name", text: $saveName).textFieldStyle(.roundedBorder).onSubmit(commitSave).frame(maxWidth: 150)
                    Button("Save", action: commitSave).buttonStyle(CapsuleButtonStyle())
                    Button("Cancel") { saving = false }.buttonStyle(CapsuleButtonStyle())
                } else {
                    Button("Save queue") { saveName = ""; saving = true }.buttonStyle(CapsuleButtonStyle())
                        .disabled(state.player.queue.isEmpty)
                }
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

    private func commitSave() { state.saveQueue(named: saveName); saving = false; tab = .saved }

    @ViewBuilder private var savedRows: some View {
        let list = state.savedQueues.queues
        if list.isEmpty { Text("No saved queues yet. Save the queue to bring it back later.").foregroundStyle(CU.muted).padding(8) }
        ForEach(list) { q in
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(q.name).fontWeight(.semibold).lineLimit(1)
                    Text("\(q.items.count) songs · \(q.minutes) min").font(.system(size: 12)).foregroundStyle(CU.muted)
                }
                Spacer(minLength: 4)
                Button("Play") { state.playSavedQueue(q.id) }.buttonStyle(CapsuleButtonStyle())
                Menu {
                    Button("Add to queue") { state.addSavedQueue(q.id) }
                    Divider()
                    Button("Delete", role: .destructive) { state.savedQueues.remove(q.id) }
                } label: { Image(systemName: "ellipsis.circle") }
                .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
                .accessibilityLabel("Actions for \(q.name)")
            }
            .padding(.horizontal, 8).padding(.vertical, 6)
            .accessibilityElement(children: .contain)
        }
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
                ReorderRow(index: i, count: up.count, move: { p.moveUpNext(from: $0, to: $1) }) { grab in
                songRow(item, time: PlayerModel.clock(item.duration), playing: false, grab: grab) {
                    Menu {
                        Button("Play now") { p.jump(toUpNext: i) }
                        Button("Move up") { p.moveUpNext(from: i, to: i - 1) }.disabled(i == 0)
                        Button("Move down") { p.moveUpNext(from: i, to: i + 1) }.disabled(i == up.count - 1)
                        if state.radio.sonicAvailable { Button("Sonic path from playing song") { state.showSonicPath(to: item) } }
                        Divider()
                        Button("Remove from queue", role: .destructive) { p.removeUpNext(at: i) }
                    } label: { Image(systemName: "ellipsis.circle") }
                    .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
                    .accessibilityLabel("Actions for \(item.title)")
                }
                }
            }
        }
    }

    private func songRow<T: View>(_ q: QueueItem, time: String, playing: Bool, grab: ReorderGrab? = nil, @ViewBuilder trailing: () -> T = { EmptyView() }) -> some View {
        HStack(spacing: 11) {
            HStack(spacing: 11) {
            CoverView(album: AlbumItem(id: -1, title: q.album, artist: q.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: q.coverArt))
                .frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous)).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(q.artist).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            }
            .modifier(grab ?? ReorderGrab())
            HStack(spacing: 4) {
                if playing { PlayingBars(active: state.player.isPlaying) }
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
            seg("Up Next", on: tab == .upNext) { tab = .upNext }
            seg("History", on: tab == .history) { tab = .history }
            seg("Saved", on: tab == .saved) { tab = .saved }
        }
        .padding(3).background(Color(red: 0.47, green: 0.47, blue: 0.5).opacity(0.14), in: Capsule())
    }

    private func seg(_ t: String, on: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).font(.system(size: 13, weight: on ? .semibold : .medium)).lineLimit(1).fixedSize().padding(.horizontal, 14).padding(.vertical, 3)
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
